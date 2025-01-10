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

def extract_constraints_template_onlyAllowed(description, feature_key):
    """
    Genera restricciones UVL para template.spec.restartPolicy basadas en los valores que se permiten segun las descripciones
    
    Maneja dos casos:
    1. Un único valor permitido: "Always".
    2. Dos valores permitidos: "Never" o "OnFailure".
    
    Args:
        description (str): Descripción de la característica.
        feature_key (str): Nombre de la característica.

    Returns:
        str: Restricción UVL generada.
    """
    template_spec_policy_pattern01 = re.compile(r'(?<=The only allowed template.spec.restartPolicy value is\s)\"([A-Za-z]+)\"', re.IGNORECASE) ## Entre parentesis añade las comillas dobles tambien
    template_spec_policies_pattern02 = re.compile(r'\"([A-Za-z]+)\"') ## expresión que captura los valores que vienen entre comillas: caso 2
    #uvl_rule =""
    feature_with_spec = f"{feature_key}_spec_restartPolicy"
    
    if 'value is' in description: ### Caso en el que solo hay un único valor posible para template.spec.restartPolicy: Always
        policy_match = template_spec_policy_pattern01.search(description)
        if not policy_match:
            raise ValueError(f"No se encontró un valor único en la descripción: {description}")
        policy_Always = f"{feature_with_spec}_{policy_match.group(1)}"
        ## Se definen los otros 2 casos posibles de valores. No estan presentes en las descripciones que se obtienen por lo que se agregan directamente
        policy_OnFailure = f"{feature_with_spec}_OnFailure"
        policy_Never = f"{feature_with_spec}_Never" 

        return f"({feature_key} => {policy_Always} & !{policy_Never} & !{policy_OnFailure})"

    elif 'values are' in description: ### Caso en el que hay 2 valores posibles para template.spec.restartPolicy: Never y OnFailure
        policies_match = template_spec_policies_pattern02.findall(description) # Se obtienen los valores del caso de las descripciones
        policies_Always = f"{feature_with_spec}_Always"
        if len(policies_match) < 2:
            raise ValueError(f"Se esperaban al menos dos valores en la descripción: {description}")
        allowed_policies = [f"{feature_with_spec}_{policy}" for policy in policies_match]
        return f"({feature_key} => {' | '.join(allowed_policies)}) & !{policies_Always}"
    
    # Si no se cumple ninguno de los casos
    raise ValueError(f"Descripción inesperada para {feature_key}: {description}")

def extract_constraints_string_oneOf(description, feature_key):
    """ Función que trata restricciones de tipo String, en ellas: La primera obtiene restricciones en base al tipo del tipo de petición que defina el campo kind (String). Al no tener
    definido los tipos en su descripción no se los ha insertado como Booleans pero si se usa para aplicar la coincidencia y activación de los otros campos, 10 constraints. """

    uvl_rule = ""
    feature_without_lastProperty = feature_key.rsplit('_', 1)[0]

    if 'indicates which one of' in description: ## Se usa la descripción del kind para tener el feature string de los tipos que pueden ser los otros campos. Se interpreta como que solo uno de los campos puede ser seleccionado (10)
        print("No SE EJECUTA?")
        kind_authentication_group = f"{feature_without_lastProperty}_group"
        kind_authentication_serviceAccount = f"{feature_without_lastProperty}_serviceAccount"
        kind_authentication_User = f"{feature_without_lastProperty}_user"

        uvl_rule += f"({feature_key} == 'Group' => {kind_authentication_group})" \
        f" | ({feature_key} == 'ServiceAccount' => {kind_authentication_serviceAccount})" \
        f" | ({feature_key} == 'User' => {kind_authentication_User})" \
        f" & !({kind_authentication_group} & {kind_authentication_serviceAccount})" \
        f" & !({kind_authentication_serviceAccount} & {kind_authentication_User})" \
        f" & !({kind_authentication_group} & {kind_authentication_User})" 
        ## Se agregan las condiciones para que solo pueda ser cogido uno a la vez. No esta del todo claro segun la descrip. Pero se puede presuponer

    if uvl_rule is not None:
        return uvl_rule.strip() ### Devolver restricciones y eliminar las lineas en blanco
    else:
        return "El conjunto esta vacio"
def extract_constraints_multiple_conditions(description, feature_key):
    """ Función que trata restricciones 'complejas' con varias condiciones lógicas o featues involucrados. Primero se desarrollo una en la que se decían los valores que no debían de ser, por otro lado"""

    conditions_pattern = re.compile(r'\b(Approved|Denied|Failed)\b')
    type_notbe_pattern = re.compile(r'(?<=conditions may not be\s)\"([A-Za-z]+)\"\s+or\s+\"([A-Za-z]+)\"')

    uvl_rule = ""
    feature_without_lastProperty = feature_key.rsplit('_', 1)[0]
    if 'conditions may not be' in description: ## Restriccion que... (4) ## MODIFICADO
        type_match = type_notbe_pattern.search(description)
        type01 = type_match.group(1)    
        type02 = type_match.group(2)
        types_notbe = f"!{feature_key}_{type01} & !{feature_key}_{type02}"
        conditions_match = conditions_pattern.findall(description)
        uvl_rule += f"{feature_without_lastProperty} => ({feature_without_lastProperty}_type_{conditions_match[0]} | {feature_without_lastProperty}_type_{conditions_match[1]} | {feature_without_lastProperty}_type_{conditions_match[2]}) => {types_notbe}"
    elif 'Details about a waiting' in description: ## Solo se procesara una de las descripciones y se introduciran los otros features estaticamente. Al ser 3 valores y no haber una descrip con estas se agregaran los otros 2 manualmente...
        ## waiting {default} // feature_key {default} ## Funcion que define el estado de un contenedor con 3 posibles opciones. Solo se puede seleccionar una (21)
        print("No SE EJECUTA?")
        container_state01 = f"{feature_without_lastProperty}_running"
        container_state02 = f"{feature_without_lastProperty}_terminated"
        uvl_rule += f"{feature_without_lastProperty} => ({feature_key} => !{container_state01} & !{container_state02})" \
        f" & ({container_state01} => !{feature_key} & !{container_state02})" \
        f" & ({container_state02} => !{feature_key} & !{container_state01})"
        uvl_rule += f"& (!{container_state01} & !{container_state02} => {feature_key})" ### Regla por defecto, si no hay otro seleccionado, se selecciona por defecto waiting..
    elif 'TCPSocket is NOT' in description: ## Restricciones sin patron, no viene definido en las descr de los sub-features involucrados (175)
        """ Nuevo grupo basado en la descrip: sin patron, descripcion principal: lifecycleHandler defines a specific action that should be taken in a lifecycle hook. One and only one of the fields, except TCPSocket must be specified. """
        action_lifecycle_exec = f"{feature_without_lastProperty}_exec"
        action_lifecycle_httpGet =f"{feature_without_lastProperty}_httpGet"
        action_lifecycle_sleep = f"{feature_without_lastProperty}_sleep"
        
        uvl_rule += f"{feature_without_lastProperty} => ({action_lifecycle_exec} | {action_lifecycle_httpGet} | {action_lifecycle_sleep})" \
        f" & !({action_lifecycle_exec} & {action_lifecycle_httpGet})" \
        f" & !({action_lifecycle_exec} & {action_lifecycle_sleep})" \
        f" & !({action_lifecycle_httpGet} & {action_lifecycle_sleep})" \
        f" & !{feature_key}" ## No es valido para este feature: encadena varios dead features por parte de otras restricciones de rangos _...tpcSocket_port...

        #if feature_without_lastProperty.endswith('LifecycleHandler'):
        #    uvl_rule += f" & !{feature_key}"

    if uvl_rule is not None:
        return uvl_rule.strip() ### Devolver restricciones y eliminar las lineas en blanco
    else:
        return "El conjunto esta vacio"

def extract_constraints_primary_or(description, feature_key):
    """ Función que extrae las restricciones de las descripciones que contienen "Exactly one of" en las descripciones generales de los features. Pero en este caso el programa
    esta diseñado para no coger estas descripciones de primer nivel por evitar incongruencias. De ese modo, se realizarán las inserciones de las constraints de manera más especifica
    usando las descripciones y palabras para obtener los features involucrados en las descripciones de los features de primer nivel."""

    uvl_rule = ""
    feature_without_lastProperty = feature_key.rsplit('_', 1)[0]

    if 'non-resource access request' in description: ## Exactly one of 
        resourceAtr01 = f"{feature_without_lastProperty}_resourceAttributes"
        uvl_rule = f"{feature_without_lastProperty} => ({feature_key} | {resourceAtr01}) & !({feature_key} & {resourceAtr01})"
    elif 'succeededIndexes specifies' in description: ## Each rule must have at least one of the
        resourceAtr02 = f"{feature_without_lastProperty}_succeededCount" ## (9)
        uvl_rule = f"{feature_without_lastProperty} => {feature_key} | {resourceAtr02}"
    elif 'Represents the requirement on the container' in description: ## Adición de un grupo con una regla "compleja" en la que tiene que haber un feature activo pero no se pueden los 2 a la vez (9)
        resourceAtr03 = f"{feature_without_lastProperty}_onPodConditions" ## One of onExitCodes and onPodConditions, but not both,
        uvl_rule = f"{feature_without_lastProperty} => ({feature_key} | {resourceAtr03}) & !({feature_key} & {resourceAtr03})"
    elif 'ResourceClaim object in the same namespace as this pod' in description: ## Se convierte y asume que "ClaimSource describes a reference to a ResourceClaim.\n\nExactly one of these fields should be set.", se pasa a feature1 XOR feature2
        resourceAtr04 = f"{feature_without_lastProperty}_resourceClaimTemplateName" ## ()
        uvl_rule = f"{feature_without_lastProperty} => ({feature_key} | {resourceAtr04}) & !({feature_key} & {resourceAtr04})"
    elif 'datasetUUID is' in description: ## Represents a Flocker volume mounted by the Flocker agent. One and only one of datasetName and datasetUUID should be set. (37)
        flocker_volume_datasetName = f"{feature_without_lastProperty}_datasetName"
        uvl_rule = f"{feature_without_lastProperty} => ({feature_key} | {flocker_volume_datasetName}) & !({feature_key} & {flocker_volume_datasetName})"

    if uvl_rule is not None:
        return uvl_rule
    else:
        return "El conjunto esta vacio"

def extract_constraints_least_one(description, feature_key):
    """ Función que extrae las restricciones de las descripciones que contienen "Exactly one of, a least one of, at least one of", basadas en la constraint de que al menos un feature debe de ser seleccionado """
    least_one_pattern01 = re.compile(r'(?<=a least one of\s)(\w+)\s+or\s+(\w+)', re.IGNORECASE) #  Expresión regular para obtener los 2 valores precedidos por "a least one of" y separados por un "or"
    exactly_least_one_pattern02 = re.compile(r'(?<=Exactly one of\s)`(\w+)`\s+or\s+`(\w+)`', re.IGNORECASE) #  Expresión regular para los valores precedidos por "Exactly..." y que se encuentren bajo comillas invertidas separados por un "or" (8, url, service)
    at_least_one_pattern01 = re.compile(r'(?<=At least one of\s)`(\w+)`\s+and\s+`(\w+)`', re.IGNORECASE) #  Expresión regular para los valores precedidos por "At..." y que se encuentran como en el anterior, bajo comillas invertidas y separadas por un "and"

    uvl_rule = ""

    feature_without_lastProperty = feature_key.rsplit('_', 1)[0]
    a_least_match01 = least_one_pattern01.search(description)
    exactly_match01 = exactly_least_one_pattern02.search(description)
    at_least_match01 = at_least_one_pattern01.search(description)

    if a_least_match01: ## Si hay coincidencia con la primera expresión se agrega la regla/constraint definida
        value01 = a_least_match01.group(1)
        value02 = a_least_match01.group(2)

        uvl_rule = f"{feature_without_lastProperty} => {feature_without_lastProperty}_{value01} | {feature_without_lastProperty}_{value02}"
    elif exactly_match01: ## Si hay coincidencia con la segunda expresión se agrega la constraint definida
        print("Comprobacion02", exactly_match01)
        value01 = exactly_match01.group(1)
        value02 = exactly_match01.group(2)

        uvl_rule = f"{feature_without_lastProperty} => ({feature_without_lastProperty}_{value01} | {feature_without_lastProperty}_{value02}) & !({feature_without_lastProperty}_{value01} & {feature_without_lastProperty}_{value02})"
    elif at_least_match01: ## Si hay coincidencia con la tercera expresión se agrega la constraint definida
        value01 = at_least_match01.group(1)
        value02 = at_least_match01.group(2)

        uvl_rule = f"{feature_without_lastProperty} => {feature_without_lastProperty}_{value01} | {feature_without_lastProperty}_{value02}"

    if uvl_rule is not None:
        return uvl_rule
    else:
        return "El conjunto esta vacio"


def extract_constraints_operator(description, feature_key):
    """ Función que extrae las restricciones de las descripciones que contienen "If the operator is" con posibles valores y opciones de selección de features"""
    # Expresión regular para "Requires (X, Y) when feature is up" ## Se ha definido el orden de seleccion del feature o no por las expresiones "non-empty, empty. Si hubiese variacion se tendria en cuenta para la selección"
    operator_is_pattern01 = re.compile(r'If the operator is\s+(\w+)\s+or\s+(\w+)', re.IGNORECASE) #  Expresión regular para obtener todos los pares (X,Y) de las descripcciones con "If the operator is"
    operator_if_pattern02 = re.compile(r'If the operator is\s+(\w+)') # Expresion para las restricciones que solo tienen un único valor

    uvl_rule = ""
    feature_without_lastProperty = feature_key.rsplit('_', 1)[0]
    operator_match01 = operator_is_pattern01.findall(description)

    print("Operator 01",operator_match01)

    # Inicializar las variables para almacenar los valores de las restricciones
    required_value = None

    if  operator_match01 and 'is Exists,' not in description:
        # Capturar la propiedad y el valor de "Required when"
        type_property01 = operator_match01[0] # Captura los primeros valores del par "In or NotIn"
        type_property02 = operator_match01[1] # Captura los primeros valores del par "Exists or DoesNotExist"
        print("Required 01", type_property01)
        print("Required 02", type_property02)

        uvl_rule = f"({feature_without_lastProperty}_operator_{type_property01[0]} | {feature_without_lastProperty}_operator_{type_property01[1]} => {feature_key}) | ({feature_without_lastProperty}_operator_{type_property02[0]} |{feature_without_lastProperty}_operator_{type_property02[1]} => !{feature_key})"
        if('the operator is Gt or Lt' in description):
            type_property05 = operator_match01[2]
            uvl_rule += f"| ({feature_without_lastProperty}_operator_{type_property05[0]} |{feature_without_lastProperty}_operator_{type_property05[1]} => {feature_key})"

    elif 'is Exists' in description: ## Caso en el que solo hay un valor y se usa una captura diferente (32 descripciones)
        operator_match02 = operator_if_pattern02.search(description)
        required_value = operator_match02.group(1)
        uvl_rule = f"{feature_without_lastProperty}_operator_{required_value} => {feature_key}"

    if uvl_rule is not None:
        return uvl_rule
    else:
        return "El conjunto esta vacio"

def extract_constraints_os_name(description, feature_key):
    """ Metodo para extraer las restricciones que definen el posible uso de features o no en base al sistema operativo que se seleccione: windows o linux"""

    osName_pattern = re.compile(r'(?<=Note that this field cannot be set when spec.os.name is\s)([a-zA-Z\s,]+)(?=\.)', re.IGNORECASE) # re.compile(r'\`([A-Za-z]+)\`')
    uvl_rule =""
    osName_match = osName_pattern.search(description)
    path_osName = "os_name"
    print("Los SO son: ",osName_match)
    list_anothers = ['_v1_Container_securityContext_', '_v1_EphemeralContainer_securityContext_', '_PodSecurityContext_', '_v1_SecurityContext_']

    if osName_match and '_template_spec_' in feature_key: ## Dependiendo de que grupo pertenece el feature_os_name es distinto, grupo principal de 1247 features
        match = re.search(r'^(.*?_template_spec)', feature_key) #(r'^(.*?_template_spec)')

        if match:
            feature_without0 = match.group(1)
            print("EL FEATURE DEL MATCH ES ",feature_without0)
        else:
            print("ERROR EN EL MATCH DE feature_key")

        name_obtained = osName_match.group(1) ## Obtener el nombre del patron obtenido

        uvl_rule = f"{feature_without0}_{path_osName}_{name_obtained} => !{feature_key}"

    elif osName_match and '_Pod_spec_' in feature_key: ## Caso del segundo grupo, _Pod_spec_, 43 features
        match = re.search(r'^(.*?_Pod_spec)', feature_key) #(r'^(.*?_template_spec)')

        if match:
            feature_without0 = match.group(1)
            print("EL FEATURE DEL MATCH ES ",feature_without0)
        else:
            print("ERROR EN EL SEGUNDO MATCH DE feature_key")

        name_obtained = osName_match.group(1) ## Obtener el nombre del patron obtenido
        uvl_rule = f"{feature_without0}_{path_osName}_{name_obtained} => !{feature_key}"


    elif osName_match and '_PodList_items_spec_' in feature_key: ## Caso del tercer grupo, _PodList_items_spec_, 43 features
        
        match = re.search(r'^(.*?_PodList_items_spec)', feature_key) #(r'^(.*?_template_spec)')
        feature_without0 = match.group(1)
        name_obtained = osName_match.group(1) ## Obtener el nombre del patron obtenido
        uvl_rule = f"{feature_without0}_{path_osName}_{name_obtained} => !{feature_key}"

    elif osName_match and '_core_v1_PodSpec_' in feature_key: ## Caso del cuarto grupo, _core_v1_PodSpec, 43 features

        match = re.search(r'^(.*?_core_v1_PodSpec)', feature_key) #(r'^(.*?_template_spec)')

        feature_without0 = match.group(1)
        name_obtained = osName_match.group(1) ## Obtener el nombre del patron obtenido
        uvl_rule = f"{feature_without0}_{path_osName}_{name_obtained} => !{feature_key}"

    elif osName_match and '_PodTemplateSpec_spec_' in feature_key: ## Caso del quinto grupo, _PodTemplateSpec_spec_, 43 features

        match = re.search(r'^(.*?_PodTemplateSpec_spec)', feature_key) #(r'^(.*?_template_spec)')
        feature_without0 = match.group(1)
        name_obtained = osName_match.group(1) ## Obtener el nombre del sistema operativo
        uvl_rule = f"{feature_without0}_{path_osName}_{name_obtained} => !{feature_key}"

    elif osName_match and any(pattern in feature_key for pattern in list_anothers): ## Caso del grupo sin feature spec: grupo general

        predefined_feature_os = "io_k8s_api_core_v1_PodSpec_os_name"        
        name_obtained = osName_match.group(1) ## Obtener el nombre del patron obtenido

        uvl_rule = f"{predefined_feature_os}_{name_obtained} => !{feature_key}"

    if uvl_rule is not None:
        return uvl_rule
    else:
        print("UVL RULE ESTA VACÍO")


def extract_constraints_mutualy_exclusive(description, feature_key):
    """ Metodo para extraer las restricciones de exclusion mutua encontradas en _name y _selector"""
    ## Para este caso hay 12 descript que no se acceden porque no hace falta al tener en cada par la misma ref, con procesar una equivale a las 2

    exclusive_pattern = re.compile(r'\`([A-Za-z]+)\`')
    uvl_rule =""
    exclusive_match = exclusive_pattern.findall(description)
    feature_without_lastProperty = feature_key.rsplit('_', 1)[0]

    if exclusive_match:
        type_property01 = exclusive_match[0] ## Hay valores repetidos pero solo se acceden a los 2 primeros
        type_property02 = exclusive_match[1]
        uvl_rule = f"({feature_without_lastProperty}_{type_property01} => !{feature_without_lastProperty}_{type_property02}) & ({feature_without_lastProperty}_{type_property02} => !{feature_without_lastProperty}_{type_property01})"
    
    if uvl_rule is not None:
        return uvl_rule
    else:
        print("UVL RULE ESTA VACÍO")

## Función para convertir constraints strings y requires 
def extract_constraints_if(description, feature_key): 
    """ Metodo para extraer las restricciones "generales" de only if type, Must be set if type is, This field MUST be empty if: relacionadas con _RollingUpdate, _Localhost, _Limited, _Exempt"""

    only_if_pattern = re.compile(r'\"([A-Za-z]+)\"')
    ##if_exempt_pattern = re.compile(r'\"([A-Za-z]+)\"')
    #only_if_pattern = re.compile(r'\"([^\"]+)\"')

    uvl_rule =""
    if_match = only_if_pattern.search(description)
    feature_without_lastProperty = feature_key.rsplit('_', 1)[0]

    if if_match and 'exempt' not in feature_key: ### Trata de las descipciones con el patrón "Must be set if type is"
        value_obtained = if_match.group(1) ## Obtener el valor del patron obtenido
        if 'Must be set if type is' in description or 'Must be set if and only if type' in description or 'may be non-empty only if' in description: ## Agregado nuevo conjunto may be non-empty only if (10)
            uvl_rule = f"{feature_without_lastProperty}_type_{value_obtained} <=> {feature_key}"
        else:
            ## Division entre los tipos por si solo se puede acceder al feature si el tipo es el concretado
            uvl_rule = f"{feature_without_lastProperty}_type_{value_obtained} => {feature_key}" ## No se si haria falta los 2 #### PARTE QUIZAS REDUNDANTE(Preguntar): | (!{feature_without_lastProperty}_type_{value_obtained} => !{feature_key})

    elif 'exempt' in feature_key: ### Trata de las descripciones con el patrón "This field MUST be empty if:"
        exempt_match = only_if_pattern.findall(description)
        #exempt_match = set(exempt_match) ## hay valores repetidos pero solo se acceden a los 2 primeros
        print("Lo que captura el patron", exempt_match)
        type_property01 = exempt_match[0] # Limited
        type_property02 = exempt_match[1] # Exempt
        print("Valores exempt capturados", exempt_match)
        print(f"{type_property01}, tipo2: {type_property02}")
        uvl_rule = f"({feature_without_lastProperty}_type_{type_property01} => !{feature_key}) | ({feature_without_lastProperty}_type_{type_property02} => {feature_key})" ### Aqui se especifican los 2 casos
        
    if uvl_rule is not None:
        return uvl_rule
    else:
        return "No hay ninguna coincidencia con los patrones y descripciones"

def extract_constraints_required_when(description, feature_key):
    # Expresión regular para "Required when X is set to Y"
    required_when_pattern = re.compile(r'Required when\s+(\w+)\s+is\s+set\s+to\s+"([^"]+)"', re.IGNORECASE)
    # Expresión regular para "Must be unset when X is set to Y"
    must_be_unset_pattern = re.compile(r'must be unset when\s+(\w+)\s+is\s+set\s+to\s+"([^"]+)"', re.IGNORECASE)
    # Expresión regular para "Required when `X` is set to `Y`"
    required_when_pattern_strategy = re.compile(r'Required when\s+`(\w+)`\s+is\s+set\s+to\s+`?\"?([^\"`]+)\"?`?', re.IGNORECASE)

    uvl_rule = ""
    feature_without_lastProperty = feature_key.rsplit('_', 1)[0]
    # Buscar coincidencias para "Required when"
    required_match = required_when_pattern.search(description)
    unset_match = must_be_unset_pattern.search(description)
    when_match = required_when_pattern_strategy.search(description)

    # Inicializar las variables para almacenar los valores de las restricciones
    required_property, required_value = None, None
    unset_property, unset_value = None, None

    if  required_match and unset_match:
        # Capturar la propiedad y el valor de "Required when"
        required_property = required_match.group(1)
        required_value = required_match.group(2)
        print(f"COINCIDENCIA REQUERIDA: {required_property} = {required_value}")
        uvl_rule = f"{feature_without_lastProperty}_{required_property}_{required_value} => {feature_key}"
        
        unset_property = unset_match.group(1)
        unset_value = unset_match.group(2)
        uvl_rule += f" & !({feature_without_lastProperty}_{unset_property}_{unset_value})"

    elif when_match and not required_match and not unset_match:
        value_property = when_match.group(1)  # Captura la propiedad (strategy o scope)
        value_default = when_match.group(2)  # Captura el valor (Webhook o Namespace)
        # Ajusta el feature_key según tu formato
        feature_without_lastProperty = feature_key.rsplit('_', 1)[0]
        # Genera la regla UVL para "Required when"
        uvl_rule = f"{feature_without_lastProperty}_{value_property}_{value_default} => {feature_key}"

    if uvl_rule is not None:
        return uvl_rule
    else:
        return "El conjunto esta vacio"


def extract_minimum_value(description, feature_key):
    """ Funcion para extraer las restricciones del valor minimo que expresan varios patrones en algunas descripciones. Se basa en usar los patrones y expresiones para capturar los enteros que delimitan y 
    forman parte de un rango. También se ha añadido un rango por el momento**"""

    value_minimum_pattern = re.compile(r'(?<=Minimum value is\s)(\d+)')
    value_text_pattern = re.compile(r'(?<=minimum valid value for expirationSeconds is\s)(\d+)')
    in_the_range_pattern = re.compile(r'(?<=in the range\s)(\d+)-(\d+)')

    uvl_rule =""
    minimum_match = value_minimum_pattern.search(description)
    minimum_text_match = value_text_pattern.search(description)
    range_match = in_the_range_pattern.search(description)


    if minimum_match: ## (1295)
        uvl_rule = f"{feature_key} > {minimum_match.group(1)}"
    elif not minimum_match and "Value must be non-negative" in description: ## (36)
        uvl_rule = f"{feature_key} > 0"
    elif minimum_text_match: ## (3)
        print(f"El minimo tiene que ser 600: ", minimum_text_match)
        uvl_rule = f"{feature_key} > {minimum_text_match.group(1)}"
    elif range_match: ## (92)
        print(f"LOS RANGE MATCH SON: {range_match.group(2)}")
        uvl_rule = f"{feature_key} > {range_match.group(1)} & {feature_key} < {range_match.group(2)}"
        
    if uvl_rule is not None:
        return uvl_rule ## 1426
    # Si no se cumple ninguno de los casos
    raise ValueError(f"Descripción inesperada para {feature_key}: {description}")


# Función para extraer límites si están presentes en la descripción
def extract_bounds(description):
    #doc = nlp(description)
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

    ### Adicion restriccion con palabras: must be between
    between_text_pattern = re.compile(r'must\s+be\s+between\s+(\d+)\s+and\s+(\d+)', re.IGNORECASE)

    ## Minimum value is

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
        
    # Detectar rangos de la forma "must be between 0 and 100" y "...1 and 30". El rango 1-30 son segundos y el rango 0-100 representa "niveles" de prioridad. Tot: 22 restric
    between_text_match = between_text_pattern.search(description) 
    if between_text_match:
        min_bound = int(between_text_match.group(1))
        max_bound = int(between_text_match.group(2))
        is_other_number = True
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
    #count_requireds = 0
    # Extraer límites si están presentes
    min_bound, max_bound, is_port_number, is_other_number = extract_bounds(description)
    #min_bound01, is_other_number = extract_min_max(description)
    # Ajustar los patrones para generar sintaxis UVL válida según el tipo de datos
    if type_data == "Boolean" or type_data == "boolean":
        #if any(tok.lemma_ == "slice" and tok.text in description for tok in doc):
        #    print("")
        #elif "empty" in description: 
        #    uvl_rule = f"!{feature_key}"
        if "Number must be in the range" in description:
            feature_without_lastProperty = feature_key.rsplit('_', 1)[0]
            uvl_rule = f"{feature_without_lastProperty} => ({feature_key}_asInteger > 1 & {feature_key}_asInteger < 65535) | ({feature_key}_asString == 'IANA_SVC_NAME')" ## Ver como añadir ese formato
            #uvl_rule = f"{feature_key} => ({feature_key}_asInteger > 1 & {feature_key}_asInteger < 65535) | ({feature_key}_asString == 'IANA_SVC_NAME')" ## Ver como añadir ese formato
        elif "required when" in description or 'Required when' in description:
            const = extract_constraints_required_when(description, feature_key)
            uvl_rule = const
        elif "only if type" in description or "Must be set if type is" in description or "must be non-empty if and only if" in description or "field MUST be empty if" in description or "may be non-empty only if" in description: ## Agregado nuevo conjunto 15/11: Queue (10) 
            first_constraint = extract_constraints_if(description, feature_key)
            uvl_rule = first_constraint
        elif "selector can be used to match multiple param objects based on their labels" in description:
            constraint = extract_constraints_mutualy_exclusive(description, feature_key)
            print("Restricciones", constraint)
            uvl_rule = constraint
        elif "Note that this field cannot be" in description:
            constraint = extract_constraints_os_name(description, feature_key)
            #print("DEBERIA DE FUNKAR: ", constraint)
            uvl_rule = constraint
        elif "If the operator is" in description: ## add in description
            constraint = extract_constraints_operator(description, feature_key)
            uvl_rule = constraint
        elif "a least one of" in description or "Exactly one of" in description or "At least one of" in description:
            constraint = extract_constraints_least_one(description, feature_key) ## Probando sin
            print("CONSTRAINT ES ")
            uvl_rule = constraint
        elif "resource access request" in description or "succeededIndexes specifies" in description or "Represents the requirement on the container" in description or "ResourceClaim object in the same namespace as this pod" in description or "datasetUUID is" in description:
            uvl_rule = extract_constraints_primary_or(description, feature_key)
            print("NADA")
        elif "conditions may not be" in description or "Details about a waiting" in description or "TCPSocket is NOT" in description:
            constraint = extract_constraints_multiple_conditions(description, feature_key)
            print("FUNKA BIEN?")
            uvl_rule = constraint
        elif "template.spec.restartPolicy" in description in description:
            uvl_rule = extract_constraints_template_onlyAllowed(description, feature_key)
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
        elif "Minimum value is" in description or "Value must be non-negative" in description or "minimum valid value for" in description or "in the range" in description:
            uvl_rule = extract_minimum_value(description, feature_key)
            if "in the range" in description:
                print("LA REGLA ES, ", uvl_rule)
        #if is_other_number:  ## posible uso para diferenciar casos especificos mas adelante
        #    # Si es un número de puerto, asegurarse de usar los límites de puerto
        #    min_bound = 0 if min_bound is None else min_bound
        #    max_bound = 1800 if max_bound is None else max_bound
 
    elif type_data == "" or type_data == "string":
        if 'conditions may not be' in description:
            constraint = extract_constraints_multiple_conditions(description, feature_key)
            print("It does?")
            uvl_rule = constraint
        elif 'indicates which one of' in description:
            constraint = extract_constraints_string_oneOf(description, feature_key)
            print("It works?")
            uvl_rule = constraint

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