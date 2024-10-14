import json
import spacy
import re

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
    is_port_number = False

    # Expresiones para detectar intervalos de la forma "0 < x < 65536", "1-65535 inclusive", y "Number must be in the range 1 to 65535"
    range_pattern = re.compile(r'(\d+)\s*<\s*\w+\s*<\s*(\d+)')
    inclusive_range_pattern = re.compile(r'(\d+)\s*-\s*(\d+)\s*\(inclusive\)')
    range_text_pattern = re.compile(r'Number\s+must\s+be\s+in\s+the\s+range\s+(\d+)\s+to\s+(\d+)', re.IGNORECASE)
    range_text_pattern = re.compile(r'(?<=Number must be in the range)\s*(\d+)\s*to\s*(\d+)(?=\.)', re.IGNORECASE)

    # Detectar si la descripción menciona puertos válidos
    if "valid port number" in description.lower():
        is_port_number = True

    # Detectar rangos con "< x <" (ej. 0 < x < 65536)
    range_match = range_pattern.search(description)
    if range_match:
        min_bound = int(range_match.group(1))
        max_bound = int(range_match.group(2))
        return min_bound, max_bound, is_port_number

    # Detectar rangos con "1-65535 inclusive"
    inclusive_match = inclusive_range_pattern.search(description)
    if inclusive_match:
        min_bound = int(inclusive_match.group(1))
        max_bound = int(inclusive_match.group(2))
        return min_bound, max_bound, is_port_number

    # Detectar rangos de la forma "Number must be in the range 1 to 65535"
    range_text_match = range_text_pattern.search(description)
    if range_text_match:
        min_bound = int(range_text_match.group(1))
        max_bound = int(range_text_match.group(2))
        return min_bound, max_bound, is_port_number

    # Si no se detecta un rango explícito, intentar extraer cualquier número aislado
    numbers = [int(n) for n in re.findall(r'\d+', description)]

    # Reglas para límites mínimos y máximos basados en expresiones comunes
    if "greater than" in description or "above" in description:
        min_bound = max(numbers) if numbers else None
    elif "less than" in description or "below" in description:
        max_bound = min(numbers) if numbers else None

    return min_bound, max_bound, is_port_number

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
    min_bound, max_bound, is_port_number = extract_bounds(description)

    # Ajustar los patrones para generar sintaxis UVL válida según el tipo de datos
    if type_data == "Boolean" or type_data == "boolean":
        if any(tok.lemma_ == "slice" and tok.text in description for tok in doc):
            print("")
        elif "empty" in description: 
            uvl_rule = f"!{feature_key}"
        elif "Number must be in the range" in description:
            uvl_rule = f"{feature_key} => ({feature_key}_asInteger > 1 & {feature_key}_asInteger < 65535) | ({feature_key}_asString == 'IANA_SVC_NAME')" ## Ver como añadir ese formato
            
    elif type_data == "Integer" or type_data == "integer":
        if is_port_number:
            # Si es un número de puerto, asegurarse de usar los límites de puerto
            min_bound = 1 if min_bound is None else min_bound
            max_bound = 65535 if max_bound is None else max_bound
            uvl_rule = f"{feature_key} > {min_bound} & {feature_key} < {max_bound}"
        elif min_bound is not None and max_bound is not None:
            uvl_rule = f"{feature_key} > {min_bound} & {feature_key} < {max_bound}"
        elif min_bound is not None:
            uvl_rule = f"{feature_key} > {min_bound}"
        elif max_bound is not None:
            uvl_rule = f"{feature_key} < {max_bound}"

    elif type_data == "String":
        if "APIVersion" in description:
            uvl_rule = f"{feature_key} == 'v1' | {feature_key} == 'v1beta1' | {feature_key} == 'v2' | {feature_key} == 'v1alpha1'"
        elif "RFC 3339" in description:
            uvl_rule = f"!{feature_key}"

    # Si no hay coincidencia, incrementamos el contador de reglas no válidas
    if uvl_rule is None:
        count += 1

    return uvl_rule

# Ruta del archivo JSON
json_file_path = './descriptions_01.json'
output_file_path = './restrictions02.txt'

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
