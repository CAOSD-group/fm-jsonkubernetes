import json
import spacy

# Cargar el modelo de NLP
nlp = spacy.load("en_core_web_sm")
count = 0  # Contador de descripciones sin regla válida

# Función para cargar las características desde el archivo JSON
def load_json_features(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# Función para extraer límites si están presentes en la descripción
def extract_bounds(description):
    min_bound = None
    max_bound = None
    # Implementación para extraer los límites de min y max si es necesario
    return min_bound, max_bound

# Función para convertir descripciones en reglas UVL usando NLP
def convert_to_uvl_with_nlp(feature_key, description):
    global count
    
    # Verificar si la descripción es una lista
    if isinstance(description, list):
        description = " ".join(
            " ".join(sublist) if isinstance(sublist, list) else str(sublist) 
            for sublist in description
        )
    elif not isinstance(description, str):
        # Si no es una cadena, omitir la descripción
        print(f"Skipping non-text description for: {feature_key}")
        return None

    print(f"Processing description for: {feature_key} - {description}")

    doc = nlp(description)
    uvl_rule = None  # Inicializar como None para descripciones sin reglas válidas
    
    # Extraer límites si están presentes
    min_bound, max_bound = extract_bounds(description)

    # Ajustar los patrones para generar sintaxis UVL válida
    if any(tok.lemma_ == "slice" and tok.text in description for tok in doc):
        uvl_rule = f"{feature_key} == '*' => length({feature_key}) == 1"
    elif any(tok.lemma_ == "array" and tok.text in description for tok in doc) and "non-empty" in description:
        uvl_rule = f"length({feature_key}) > 0"
    elif any(tok.lemma_ == "array" and tok.text in description for tok in doc) and "empty" in description:
        uvl_rule = f"length({feature_key}) == 0"
    elif any(tok.lemma_ == "map" for tok in doc):
        uvl_rule = f"{feature_key}.type == 'map'"
    elif "URL" in description and "https" in description:
        uvl_rule = f"{feature_key}.startsWith('https://')"
    elif "TimeoutSeconds" in description:
        uvl_rule = f"{feature_key} > 0 && {feature_key} <= 30"
    elif "APIVersion" in description:
        uvl_rule = f"{feature_key} in ['v1', 'v1beta1']"
    elif "Kind" in description:
        uvl_rule = f"{feature_key} != null"  # Ajustado para indicar que Kind debe estar presente
    elif "Annotations" in description:
        uvl_rule = f"{feature_key}.type == 'map'"
    elif "timestamp" in description:
        uvl_rule = f"{feature_key} != null"  # Indicador genérico para timestamp
    elif "seconds" in description:
        if min_bound is not None and max_bound is not None:
            uvl_rule = f"{feature_key} > {min_bound - 1} & {feature_key} < {max_bound + 1}"
        elif min_bound is not None:
            uvl_rule = f"{feature_key} > {min_bound - 1}"
        elif max_bound is not None:
            uvl_rule = f"{feature_key} < {max_bound + 1}"
        else:
            uvl_rule = f"{feature_key} > 0"  # Caso por defecto para segundos si no hay límites específicos
    elif "RFC 3339" in description:
        uvl_rule = f"{feature_key} != null"  # Ajustado para indicar que el valor debe estar presente
    elif "empty before" in description:
        uvl_rule = f"length({feature_key}) == 0"
    elif "sequence number" in description:
        uvl_rule = f"{feature_key} > 0"  # Ajustado para indicar un valor numérico positivo
    elif "finalizers" in description:
        uvl_rule = f"DeletionTimestamp != null => length({feature_key}) == 0"
    elif "generation" in description:
        uvl_rule = f"{feature_key} > 0"
    elif "managedFields" in description:
        uvl_rule = f"{feature_key} != null"
    elif "name" in description and "unique" in description:
        uvl_rule = f"{feature_key} != null"
    elif "namespace" in description and "DNS_LABEL" in description:
        uvl_rule = f"{feature_key} != null"
    elif "ownerReferences" in description:
        uvl_rule = f"{feature_key} != null"
    elif "selfLink" in description:
        uvl_rule = f"{feature_key} == null"
    elif "uid" in description:
        uvl_rule = f"{feature_key} != null"
    elif "remainingItemCount" in description:
        uvl_rule = f"{feature_key} >= 0"
    elif "namespace" in description and "paramKind" in description:
        uvl_rule = f"{feature_key} != null"
    elif "conditions" in description:
        uvl_rule = f"{feature_key} != null"
    elif "observedGeneration" in description:
        uvl_rule = f"{feature_key} >= 0"
    elif "namespaceSelector" in description:
        uvl_rule = f"{feature_key} != null"
    elif "name" in description and "resource" in description:
        uvl_rule = f"{feature_key} != null"
    elif "decodableVersions" in description:
        uvl_rule = f"{feature_key} != null"
    elif "commonEncodingVersion" in description:
        uvl_rule = f"{feature_key} != null"
    elif "minReadySeconds" in description:
        uvl_rule = f"{feature_key} >= 0"
    elif "template" in description:
        uvl_rule = f"{feature_key} != null"
    elif "activeDeadlineSeconds" in description:
        uvl_rule = f"{feature_key} > 0"
    elif "preferredDuringSchedulingIgnoredDuringExecution" in description:
        uvl_rule = f"{feature_key} != null"
    else:
        count += 1  # Incrementar el contador si no se encontró una regla válida

    return uvl_rule


# Ruta del archivo JSON
json_file_path = 'descriptions_01.json'
output_file_path = 'C:/projects/investigacion/scriptJsonToUvl/restrictions.txt'

# Cargar datos
features = load_json_features(json_file_path)

# Aplicar la conversión a las descripciones de restricciones
uvl_rules = {}
if 'restrictions' in features:
    for restriction in features['restrictions']:
        feature_key, desc = restriction[0], restriction[1]
        # Aplicar conversión para cada descripción de restricción
        uvl_rule = convert_to_uvl_with_nlp(feature_key, desc)
        if uvl_rule:  # Solo agregar reglas válidas
            if 'restrictions' not in uvl_rules:
                uvl_rules['restrictions'] = []
            uvl_rules['restrictions'].append(f"{uvl_rule}")

# Escribir las reglas UVL generadas en el archivo de salida
with open(output_file_path, 'w', encoding='utf-8') as f:
    for rule in uvl_rules['restrictions']:
        f.write(f"{rule}\n")
        print(rule)

print(f"UVL output saved to {output_file_path}")
print(f"Hay {count} descripciones que no se pudieron transformar en restricciones UVL.")
