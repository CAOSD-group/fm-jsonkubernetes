#### Archivo que busca mapear los features de un modelo UVL a CSV. #####

import re
import csv

#uvl_model = './kubernetes_combined_02.uvl'
uvl_model_path = './kubernetes_combined_part01.uvl'

# Procesar el modelo para extraer los datos en las columnas
csv_data = []
### Rows: Feature, Midle, Turned, Value
## Example: From this feature: io_k8s_apimachinery_pkg_apis_meta_v1_APIVersions_serverAddressByClientCIDRs, we add in the ros:
## io_k8s_apimachinery_pkg_apis_meta_v1_APIVersions_serverAddressByClientCIDRs, APIVersions_serverAddressByClientCIDRs, serverAddressByClientCIDRs,
## io_k8s_api_core_v1_Pod_spec_containers_env_valueFrom_resourceFieldRef_divisor, Pod_spec_containers_env_valueFrom_resourceFieldRef_divisor, divisor,

#Como recorrer el modelo?
# Leer el archivo UVL línea por línea
with open(uvl_model_path, encoding="utf-8") as uvl_model:
    for line in uvl_model:
        # Limpiar línea y dividir por espacios
        # Limpiar línea
        line = line.strip()
        ## Se omiten/saltan las lineas que contienen mandatory, optional, alternative, namespace, features... 
        #if not re.match(r"^(String|Integer|io_k8s_)", line):   ## Alternativa de salto de expresiones que no interesan
        #    continue
        if not line.startswith(("String", "Boolean", "Integer", "io_k8s_")): # Saltar líneas que no sean features, se definen por esos 4 tipos: String, Integer o encabezado por io.. Boolean
            value_row = "-" if "cardinality" in line else "" ## Se le asigna el guión para determinar si un feature es un array
            continue

        #parts = line.split("namespace").split("features").split("Kubernetes")
        print(line)
        if "cardinality" in line:
            line_feature = line.split("cardinality")[0]
        else:
            line_feature = line.split("{")[0]
        print(line_feature)
        # Determinar si la línea contiene un tipo explícito
        parts = line_feature.split()
        print(f"Las partes divididas son: {parts}")
        if len(parts) >= 2: # Si hay tipo explícito de dato (String o Integer), extraer el nombre del feature
            feature = parts[1]
        else:
            # Si no hay tipo de dato explícito, se asume que la primera parte de las partes es el feature
            feature = parts[0]
        value_row = "-" if "cardinality" in line else "" ## Se le asigna el guión para determinar si un feature es un array

        # Obtener las partes del feature
        split_feature = feature.split("_")
        print(f"El feature del archivo es: {feature}")
        #midle = "_".join(split_feature[3:])  # Omitir las partes repetitivas (ejemplo)
        feature_aux_midle = re.search(r"[A-Z].*", feature)
        print(f"El match del feature Midle es: {feature_aux_midle}")
        midle_row = feature_aux_midle.group(0)
        print(midle_row)
        turned_row = split_feature[-1] if split_feature else ""    
        # Valor: se deja vacio o se asigna el valor si es un feature agregado que contiene el valor asignado
        value_row = turned_row if "Specific value" in line else "" ## Se define el valor y se asigna el Valor si se encuentran las palabras clave en la documentación
        print(f"VALORES: {feature}  {midle_row} {turned_row}    {value_row}")
        # Agregar al CSV
        csv_data.append([feature, midle_row, turned_row, value_row])

output_file_csv = './generateConfigs/kubernetes_mapping_features.csv'

with open(output_file_csv, mode="w", newline="") as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(["Feature, Midle, Turned, Value"])  # Encabezado
    writer.writerows(csv_data)
##generate_csv_from_uvl = (uvl_model_path)

print(f"Archivo CSV generado: {output_file_csv}")
