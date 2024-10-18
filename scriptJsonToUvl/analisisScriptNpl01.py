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
## Funcion para extraer valores de minimos en texto o sueltos

# Función para convertir texto numérico a número entero
def convert_word_to_num(word):
    return word_to_num.get(word.lower(), None)

## Función para convertir constraints strings y requires 
def extract_constraints_if(description, feature_key):

    only_if_pattern = re.compile(r'\\?["\'](.*?)\\?["\']')

    uvl_rule =""   
    if_match = only_if_pattern.search(description)
    if if_match:
        print("PORQUE SE EJECUTA?")
        value_obtained = if_match.group(1) ## Obtener el valor del patron obtenido
        feature_without_lastProperty = feature_key.rsplit('_', 1)[0]
        #print("PRUEBA rsplit", feature_without_lastProperty)
        #feature_without_lastProperty = only_if_pattern.split("_").remove[-1]
        uvl_rule = f"({feature_without_lastProperty}_type_{value_obtained} => {feature_key}) | (!{feature_without_lastProperty}_type_{value_obtained} => !{feature_key})" ## No se si haria falta los 2

        ## objetivo: io_k8s_api_apps_v1_DaemonSetUpdateStrategy_type_RollingUpdate => io_k8s_api_apps_v1_DaemonSetUpdateStrategy_rollingUpdate
        return uvl_rule
    
    return None

def extract_constraints_required(description, feature_key):
    # Expresión regular para el patrón "Required when X is set to Y"
    #required_when_pattern = re.compile(r'required when\s+`(\w+)`\s+is\s+set\s+to\s+["\'](.*?)["\']', re.IGNORECASE)
    required_when_pattern = re.compile(r'Required when\s+`(\w+)`\s+is\s+set\s+to\s+`?\"?([^\"`]+)\"?`?', re.IGNORECASE)

    # Expresión regular para el patrón "must be unset when X is set to Y"
    #must_be_unset_pattern = re.compile(r'must be unset when\s+(\w+)\s+is\s+set\s+to\s+[\'"`](.*?)[\'"`]', re.IGNORECASE)

    uvl_rule = ""
    
    # Buscar coincidencias para "Required when"
    when_match = required_when_pattern.search(description)
    if when_match:
        print("COINCIDENCIA ENCONTRADA", when_match)
        value_property = when_match.group(1)  # Captura la propiedad (strategy o scope)
        value_default = when_match.group(2)  # Captura el valor (Webhook o Namespace)
        print(f"PRIMER VALOR: {value_property} SEGUNDO VALOR: {value_default}")
        
        # Ajusta el feature_key según tu formato
        feature_without_lastProperty = feature_key.rsplit('_', 1)[0]
        
        # Genera la regla UVL para "Required when"
        uvl_rule = f"{feature_without_lastProperty}_{value_property}_{value_default} => {feature_key}"
        """
        # Buscar coincidencias para "must be unset when" (si existe)
        unset_match = must_be_unset_pattern.search(description)
        if unset_match:
            unset_property = unset_match.group(1)
            unset_value = unset_match.group(2)
            print(f"COINCIDENCIA UNSET PRIMER VALOR: {unset_property} SEGUNDO VALOR: {unset_value}")
            
            # Agregar la condición de "unset" a la regla UVL
            uvl_rule += f" & !({feature_without_lastProperty}_{unset_property}_{unset_value})"
        """
        return uvl_rule
    
    print("NO SE ENCONTRÓ COINCIDENCIA EN LA DESCRIPCIÓN")
    return None

"""
def extract_constraints_required(description, feature_key):
    #required_when_pattern = re.compile(r'Required when\s+("([^"\\]*)"|\w+).*?("([^"\\]*)")') ## , re.IGNORECASE probando solo 1
    required_when_pattern = re.compile(r'Required when\s+(\w+)\s+is\s+set\s+to\s+[\'"`](.*?)[\'"`]')
    #required_when_pattern = re.compile(r'Required when\s+(`?\w+`?)\s+is\s+set\s+to\s+\\?["\'](.*?)\\?["\']')

    uvl_rule =""  
    when_match = required_when_pattern.search(description)
    if when_match:
        print("NO SE EJECUTA?", when_match)
        value_property = when_match.group(1)
        value_default = when_match.group(2)
        print(f"PRIMER VALOR: {value_property} SEGUNDO VALOR: {value_default}")
        feature_without_lastProperty = feature_key.rsplit('_', 1)[0] ## feature principal
        
        uvl_rule = f"{feature_without_lastProperty}_{value_property}_{value_default} => {feature_key}"
        return uvl_rule
    
    return None
"""

# Función para extraer límites si están presentes en la descripción
def extract_bounds(description):
    doc = nlp(description)
    min_bound = None
    max_bound = None
    is_port_number = False
    is_other_number = False

    # Expresiones para detectar intervalos de la forma "0 < x < 65536", "1-65535 inclusive", y "Number must be in the range 1 to 65535"
    range_pattern = re.compile(r'(\d+)\s*<\s*\w+\s*<\s*(\d+)')
    inclusive_range_pattern = re.compile(r'(\d+)\s*-\s*(\d+)\s*\(inclusive\)')
    range_text_pattern = re.compile(r'Number\s+must\s+be\s+in\s+the\s+range\s+(\d+)\s+to\s+(\d+)', re.IGNORECASE)
    #range_text_pattern = re.compile(r'(?<=Number must be in the range)\s*(\d+)\s*to\s*(\d+)(?=\.)', re.IGNORECASE)
    must_be = re.compile(r'must be greater than(?: or equal to)? (\w+)',re.IGNORECASE) ## Caso especial en el que puede ser igual a cero (?: or equal to)?
    less_than_pattern = re.compile(r'less than or equal to (\d+)', re.IGNORECASE)
    #must_be_range = re.compile(r'must be greater than or equal to (\d+)\sand\sless than or equal to(\d+)')

    # Detectar si la descripción menciona puertos válidos
    if "valid port number" in description.lower():
        is_port_number = True
    

    # Traducir palabras numéricas a números enteros dentro de la descripción
    description = description.lower()
    for word, num in word_to_num.items():
        description = description.replace(word, str(num))  # Reemplazar palabras por sus equivalentes numéricos

    # Detectar rangos con "< x <" (ej. 0 < x < 65536)
    range_match = range_pattern.search(description)
    if range_match:
        min_bound = int(range_match.group(1))
        max_bound = int(range_match.group(2))
        return min_bound, max_bound, is_port_number, is_other_number

    # Detectar rangos con "1-65535 inclusive"
    inclusive_match = inclusive_range_pattern.search(description)
    if inclusive_match:
        min_bound = int(inclusive_match.group(1))
        max_bound = int(inclusive_match.group(2))
        return min_bound, max_bound, is_port_number, is_other_number

    # Detectar rangos de la forma "Number must be in the range 1 to 65535"
    range_text_match = range_text_pattern.search(description)
    if range_text_match:
        min_bound = int(range_text_match.group(1))
        max_bound = int(range_text_match.group(2))
        return min_bound, max_bound, is_port_number, is_other_number

    # Detectar expresiones simples de "greater than" o "less than"
    greater_than_match = must_be.search(description)
    less_than_match = less_than_pattern.search(description)

    if greater_than_match:
        # Convertir si es una palabra numérica
        min_bound = int(greater_than_match.group(1)) if greater_than_match.group(1).isdigit() else convert_word_to_num(greater_than_match.group(1))
        is_other_number = True

    if less_than_match:
        # Convertir si es una palabra numérica
        max_bound = int(less_than_match.group(1)) if less_than_match.group(1).isdigit() else convert_word_to_num(less_than_match.group(1))
        max_bound = max_bound + 1 ## Para tener en cuenta el equal to 
        is_other_number = True

    return min_bound, max_bound, is_port_number, is_other_number
    
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
    second_constraint = extract_constraints_required(description, feature_key)
    #first_constraint = extract_constraints_if(description, feature_key)

    # Extraer límites si están presentes
    min_bound, max_bound, is_port_number, is_other_number = extract_bounds(description)
    #min_bound01, is_other_number = extract_min_max(description)
    # Ajustar los patrones para generar sintaxis UVL válida según el tipo de datos
    if type_data == "Boolean" or type_data == "boolean":
        if any(tok.lemma_ == "slice" and tok.text in description for tok in doc):
            print("")
        elif "empty" in description: 
            uvl_rule = f"!{feature_key}"
        elif "Number must be in the range" in description:
            uvl_rule = f"{feature_key} => ({feature_key}_asInteger > 1 & {feature_key}_asInteger < 65535) | ({feature_key}_asString == 'IANA_SVC_NAME')" ## Ver como añadir ese formato
        #elif first_constraint:
        #    uvl_rule = first_constraint
        elif second_constraint:
            print(f"Second constraint extracted for {feature_key}: {second_constraint}")  # Depuración

            uvl_rule = second_constraint
                        
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
        #if is_other_number:  ## posible uso para diferenciar casos especificos mas adelante
        #    # Si es un número de puerto, asegurarse de usar los límites de puerto
        #    min_bound = 0 if min_bound is None else min_bound
        #    max_bound = 1800 if max_bound is None else max_bound
 
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
else:
    print("Error. Restricciones vacias o nulas")

# Escribir las reglas UVL generadas en el archivo de salida
with open(output_file_path, 'w', encoding='utf-8') as f:
    for rule in uvl_rules['restrictions']:
        f.write(f"{rule}\n")
        print(rule)

print(f"UVL output saved to {output_file_path}")
print(f"Hay {count} descripciones que no se pudieron transformar en restricciones UVL.")
