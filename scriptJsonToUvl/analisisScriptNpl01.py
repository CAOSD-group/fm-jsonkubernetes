import json
import spacy

# Cargar el modelo de NLP
nlp = spacy.load("en_core_web_sm")
count = 0  # Contador de descripciones sin regla válida

# Diccionario para convertir "zero" y "one"
word_to_num = {
    "zero": 0,
    "one": 1
}

# Función para cargar las características desde el archivo JSON
def load_json_features(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# Función para extraer límites si están presentes en la descripción
def extract_bounds(description):
    doc = nlp(description)
    min_bound = None
    max_bound = None

    for i, token in enumerate(doc):
        # Intentar convertir el token a un número válido (solo "zero" y "one")
        number = None
        if token.like_num:
            try:
                number = float(token.text)  # Intentar convertir el número a flotante
            except ValueError:
                pass  # Ignorar si no se puede convertir directamente
        elif token.text.lower() in word_to_num:  # Solo procesar "zero" y "one"
            number = word_to_num[token.text.lower()]

        # Si logramos obtener un número, analizar su contexto
        if number is not None:
            if i > 0:
                prev_token = doc[i - 1]
                
                # Reglas para detectar límites mínimos
                if prev_token.text in ["at", "least", "greater", "above", "more", "over", "minimum"]:
                    if min_bound is None or number > min_bound:
                        min_bound = number
                elif prev_token.text in ["than"] and doc[i - 2].text in ["greater", "more", "larger"]:
                    if min_bound is None or number > min_bound:
                        min_bound = number
                
                # Reglas para detectar límites máximos
                if prev_token.text in ["at", "most", "less", "below", "under", "fewer", "maximum", "equal"]:
                    if max_bound is None or number < max_bound:
                        max_bound = number
                #elif prev_token.text in ["than"] and doc[i - 2].text in ["less", "fewer", "smaller"]:
                #    if max_bound is None or number < max_bound:
                #        max_bound = number

    return min_bound, max_bound

# Función para convertir descripciones en reglas UVL usando NLP
def convert_to_uvl_with_nlp(feature_key, description, type_data):
    global count
    
    # Verificar si la descripción es una lista
    if isinstance(description, list):
        description = " ".join(
            " ".join(sublist) if isinstance(sublist, list) else str(sublist) 
            for sublist in description
        )
    elif not isinstance(description, str):
        # Si no es una cadena, omitir la descripción
        print(f"No hay descripcion de texto para: {feature_key}")
        return None

    doc = nlp(description)
    uvl_rule = None  # Inicializar como None para descripciones sin reglas válidas
    
    # Extraer límites si están presentes
    min_bound, max_bound = extract_bounds(description)

    # Ajustar los patrones para generar sintaxis UVL válida según el tipo de datos
    if type_data == "Boolean" or type_data == "boolean":
        if any(tok.lemma_ == "slice" and tok.text in description for tok in doc): 
            uvl_rule = f"{feature_key}_items == '*' => {feature_key}"
        elif "empty" in description: # El feature (listas) no debe estar vacío, y si lo esta hay reglas que no se puede representar
            uvl_rule = f"!{feature_key}"
        #elif any(tok.lemma_ == "array" and tok.text in description for tok in doc) and "empty" in description: ## non-empty
        #    uvl_rule = f"!{feature_key} " # Bool Posible referenciar al anterior feature: {feature_key -1} => {feature_key}
        #elif "required" in description:
        #    uvl_rule = f"{feature_key}"
        # Otros patrones booleanos...
    
    elif type_data == "Integer" or type_data == "integer":
        if "TimeoutSeconds" in description:
            uvl_rule = f"{feature_key} > 0 & {feature_key} < 31"
        elif "sequence number" in description or "positive" in description or "non-negative" in description or "greater than 0" in description or "greater than zero" in description: #greater than 0 / greater than zero
            uvl_rule = f"{feature_key} > 0" 
        #elif "seconds" in description:
        if min_bound is not None and max_bound is not None:
                uvl_rule = f"{feature_key} > {min_bound - 1} & {feature_key} < {max_bound + 1}"
        elif min_bound is not None:
                uvl_rule = f"{feature_key} > {min_bound}"
        elif max_bound is not None:
                uvl_rule = f"{feature_key} < {max_bound}"
        #    else:
        #        uvl_rule = f"{feature_key} > 0"
        # Otros patrones enteros...

    elif type_data == "String":
        if "APIVersion" in description:
            uvl_rule = f"{feature_key} == 'v1' | {feature_key} == 'v1beta1' | {feature_key} == 'v2' | {feature_key} == 'v1alpha1'"
        elif "RFC 3339" in description:
            uvl_rule = f"!{feature_key}"
        #elif "URL" in description and "https" in description:
        #    uvl_rule = f"{feature_key}.startsWith('https://')"

    # Si no hay coincidencia, incrementamos el contador de reglas no válidas
    if uvl_rule is None:
        count += 1

    return uvl_rule

# Ruta del archivo JSON
json_file_path = 'descriptions_01.json'
output_file_path = 'C:/projects/investigacion/scriptJsonToUvl/restrictions02.txt'

# Cargar datos
features = load_json_features(json_file_path)

# Aplicar la conversión a las descripciones de restricciones
uvl_rules = {}
if 'restrictions' in features:
    for restriction in features['restrictions']:
        # Asegurarse de que restriction es un diccionario y tiene las claves necesarias
        if isinstance(restriction, dict) and 'feature_name' in restriction and 'description' in restriction and 'type_data' in restriction:
            feature_key = restriction['feature_name']
            desc = restriction['description']
            type_data = restriction['type_data']
            # Aplicar conversión para cada descripción de restricción
            uvl_rule = convert_to_uvl_with_nlp(feature_key, desc, type_data)
            if uvl_rule:  # Solo agregar reglas válidas
                if 'restrictions' not in uvl_rules:
                    uvl_rules['restrictions'] = []
                uvl_rules['restrictions'].append(f"{uvl_rule}")
        else:
            print(f"Formato inesperado en la restricción: {restriction}")

# Escribir las reglas UVL generadas en el archivo de salida
with open(output_file_path, 'w', encoding='utf-8') as f:
    for rule in uvl_rules['restrictions']:
        f.write(f"{rule}\n")
        print(rule)

print(f"UVL output saved to {output_file_path}")
print(f"Hay {count} descripciones que no se pudieron transformar en restricciones UVL.")
