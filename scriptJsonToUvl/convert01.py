import json
import re
from collections import deque

class SchemaProcessor:
    def __init__(self, definitions):
        self.definitions = definitions # Un diccionario que organiza las descripciones en tres categorías:
        self.resolved_references = {}
        self.seen_references = set()
        self.seen_features = set() ## Añadir condicion a las refs vistas para no omitir refs ya vistas
        self.processed_features = set()
        self.constraints = []  # Lista para almacenar las dependencias como constraints
        #Prueba pila para las referencias ciclicas
        #self.stact_refs = []
        # Se inicializa un diccionario para almacenar descripciones por grupo
        self.descriptions = {
            'values': [], 
            'restrictions': [],
            'dependencies': []

        }
        self.seen_descriptions = set()
        self.oneOf_refs = {'io_k8s_apimachinery_pkg_api_resource_Quantity',
                           'io_k8s_apimachinery_pkg_util_intstr_IntOrString'}
        # #/definitions/io.k8s.apimachinery.pkg.util.intstr.IntOrString
        # #/definitions/io.k8s.apimachinery.pkg.api.resource.Quantity
        # Patrones para clasificar descripciones en categorías de valores, restricciones y dependencias
        self.patterns = {
            'values': re.compile(r'(valid|values are|supported|acceptable|can be)', re.IGNORECASE),
            'restrictions': re.compile(r'(allowed|conditions|should|must be|cannot be|if[\s\S]*?then|only|never|forbidden|disallowed)', re.IGNORECASE),
            'dependencies': re.compile(r'(depends on|requires|if[\s\S]*?only if|relies on|contingent upon|related to)', re.IGNORECASE)
        }

    def sanitize_name(self, name):
        """Reemplaza caracteres no permitidos en el nombre con guiones bajos y asegura que solo haya uno con ese nombre"""
        return name.replace("-", "_").replace(".", "_").replace("$", "")

    def sanitize_type_data(self, type_data):
        if type_data in ['array', 'object']:
            return 'Boolean'
        elif type_data in ['number', 'Number']:
            return 'Integer'
        return type_data

    def resolve_reference(self, ref):
        """Resuelve una referencia a su esquema real dentro de las definiciones."""
        if ref in self.resolved_references: # Se comprueba si la referencia ya ha sido resuelta
            return self.resolved_references[ref]

        parts = ref.strip('#/').split('/') # Se divide la referencia en partes
        schema = self.definitions

        try: # Se añade el try para tratar de tener más control sobre la posible omisión de referencias
            for part in parts: # Se recorren las partes de la referencia para encontrar el esquema
                schema = schema.get(part, {})
                if not schema:
                    print(f"Warning: No se pudo resolver la siguiente referencia: {ref}") # Se usa para comprobar si hay alguna referencia que se pierde y no se procesa
                    return None

            self.resolved_references[ref] = schema
            return schema
        except Exception as e:
            print("Error al resolver la referencia: {ref}: {e}")
            return None

    def is_valid_description(self, description):
        """Verifica si una descripción es válida (No muy corta y sin repeticiones) para analizarla después en busca de restricciones"""
        if len(description) < 10:
            return False
        if description in self.seen_descriptions:
            return False
        self.seen_descriptions.add(description)
        return True

    def is_required_based_on_description(self, description):
        """Determina si una propiedad es obligatoria basándose en si aparece Required al final de su descripción"""
        return description.strip().endswith("Required.")

    def extract_values(self, description):
        """Extrae valores que están entre comillas u otros delimitadores, solo si se encuentran ciertas palabras clave"""
        if not any(keyword in description.lower() for keyword in ['values are', 'possible values are', 'following states']):
            return None
        
        value_patterns = [
            # Captura valores precedidos por un guion, permitiendo múltiples espacios y saltos de línea antes y después
            re.compile(r'-\s*([\w]+(?:Resize\w+)):'),
            
            # Captura valores entre comillas escapadas o no escapadas
            re.compile(r'\\?["\'](.*?)\\?["\']'),
            #re.compile(r'\\?["\'](.*?)\\?["\']'),  # Captura valores entre comillas simples o dobles, escapadas o no
            
            re.compile(r'(?<=Valid values are:)[\s\S]*?(?=\.)'),
            re.compile(r'(?<=Possible values are:)[\s\S]*?(?=\.)'),
            re.compile(r'(?<=Allowed values are)[\s\S]*?(?=\.)'),
            #re.compile(r'(?<=-\s)(\w+)'),   # Captura valores precedidos por un guion y espacio
            #re.compile(r'(?:\\?["\'])(.*?)(?:\\?["\'])'),  # Captura valores entre comillas escapadas o no

            # [()[\]{}] []()[{}]
        ]

        values = []
        #add_quotes = False  # Variable para verificar si se necesita añadir comillas
        for pattern in value_patterns:
            matches = pattern.findall(description)
            for match in matches:
                split_values = re.split(r',\s*|\n', match)
                for v in split_values:
                    v = v.strip()
                    # Reemplazar '*' por "estrella"
                    v = v.replace('*', 'estrella')
                    v = v.replace(' ', '_').replace('/', '_')
                    #v = v.replace('/', '_')

                    # Filtrar valores que contienen puntos, corchetes, llaves o que son demasiado largos
                    if v and len(v) <= 15 and not any(char in v for char in {'.', '{', '}', '[', ']', ':'}): # añadido / por problemas con la sintaxis
                        values.append(v)
                        #if ' ' in v:  # Si un valor contiene un espacio, Era para añadir comillas dobles "", => sintaxis
                        #    add_quotes = True

        values = set(values)  # Eliminar duplicados
        if not values:
            return None
        return values #, add_quotes  # Devuelve los valores y el nombre del feature => Quitado sensor espacio


    def categorize_description(self, description, feature_name, type_data):
        """Categoriza la descripción según los patrones predefinidos."""
        
        if not self.is_valid_description(description):
            return False
        # Entrada de descripción con datos del tipo para mejorar la precisión de las reglas
        description_entry = {
        "feature_name": feature_name,
        "description": description,
        "type_data": type_data # Adición tipo para tener el tipo de dato para las restricciones
    }

        for category, pattern in self.patterns.items():
            if pattern.search(description):
                #self.descriptions[category].append((feature_name, description))
                self.descriptions[category].append((description_entry))
                return True
        
        return False
    
    """ Tratamiendo de tipos de propiedades, oneOf y enum"""
    def process_enum():
        return
    
    def process_oneOf(self, oneOf, full_name, type_feature):
        """
        Procesa la estructura 'oneOf' y genera subcaracterísticas basadas en los tipos.
        """

        feature = {
            'name': full_name,
            'type': type_feature,  # Lo ponemos como 'optional' ya que puede ser uno de varios tipos 'optional'
            'description': f"Feature based on oneOf in {full_name}",
            'sub_features': [],
            'type_data': 'Boolean'  # Aquí definimos el tipo (por ejemplo: String, Number)
        }
        # Procesar cada opción dentro de 'oneOf'
        for option in oneOf:
            if 'type' in option: # 'type' in option:
                option_type_data = option['type'].capitalize()  # Captura el tipo (por ejemplo: string, number, integer)
                sanitized_name = self.sanitize_name(full_name)  # Limpiar el nombre completo

                # Crear subfeature con el nombre adecuado
                sub_feature = {
                    'name': f"{sanitized_name}_as{option_type_data}",
                    'type': 'alternative',  # Por defecto, lo ponemos como 'optional'option_type
                    'description': f"Sub-feature of type {option_type_data}",
                    'sub_features': [],
                    'type_data': self.sanitize_type_data(option_type_data)
                }

                # Añadir la subfeature a la lista de sub_features del feature principal
                feature['sub_features'].append(sub_feature)

        return feature


    def parse_properties(self, properties, required, parent_name="", depth=0, local_stack_refs=None):
        if local_stack_refs is None:
            local_stack_refs = []  # Crear una nueva lista para esta rama

        mandatory_features = []
        optional_features = []
        queue = deque([(properties, required, parent_name, depth)])

        while queue:
            current_properties, current_required, current_parent, current_depth = queue.popleft()

            for prop, details in current_properties.items():
                sanitized_name = self.sanitize_name(prop)
                full_name = f"{current_parent}_{sanitized_name}" if current_parent else sanitized_name

                if full_name in self.processed_features:
                    continue

                # Verificar si la propiedad es requerida basado en su descripción
                description = details.get('description', '')
                is_required_by_description = self.is_required_based_on_description(description)
                feature_type = 'mandatory' if prop in current_required or is_required_by_description else 'optional'
                # Parseo de los tipos de datos y de los no válidos
                feature_type_data = details.get('type', 'Boolean')
                feature_type_data = self.sanitize_type_data (feature_type_data) 

                description = details.get('description', '')
                if description:
                    # Categorizar la descripción
                    self.categorize_description(description, full_name, feature_type_data)

                feature = {
                    'name': full_name,
                    'type': feature_type,
                    'description': description,
                    'sub_features': [],
                    'type_data': feature_type_data
                }
                # Procesar referencias
                if '$ref' in details:
                    ref = details['$ref']
                    boolonOf = False

                    # Verificar si ya está en la pila local de la rama actual (es decir, un ciclo)
                    if ref in local_stack_refs:
                        print(f"*****Referencia cíclica detectada: {ref}. Saltando esta propiedad****")
                        # Si es un ciclo, saltamos esta propiedad pero seguimos procesando otras
                        continue

                    # Añadir la referencia a la pila local
                    local_stack_refs.append(ref)
                    ref_schema = self.resolve_reference(ref)

                    if ref_schema:
                        ## Lineas no necesarias en esta implementacion: se usarian en omision de las refs (V_1.0)
                        ref_name = self.sanitize_name(ref.split('/')[-1])
                        #self.constraints.append(f"{full_name} => {ref_name}")
                        #feature_type = 'mandatory' ## feature_type principal del feature
                                                        
                        if 'properties' in ref_schema:
                            sub_properties = ref_schema['properties']
                            sub_required = ref_schema.get('required', [])
                            #feature_type = 'mandatory'
                            # Llamada recursiva con la pila local específica de esta rama
                            sub_mandatory, sub_optional = self.parse_properties(sub_properties, sub_required, full_name, current_depth + 1, local_stack_refs)
                            # Añadir subfeatures
                            feature['sub_features'].extend(sub_mandatory + sub_optional)

                        elif 'oneOf' in ref_schema:
                            feature_type = 'mandatory' if prop in current_required or is_required_by_description else 'optional'
                            oneOf_feature = self.process_oneOf(ref_schema['oneOf'], self.sanitize_name(f"{full_name}"), feature_type) #_{ref_oneOf}
                            feature_sub = oneOf_feature['sub_features']
                            # Agregar la referencia que contiene la caracteristica oneOf
                            feature['sub_features'].extend(feature_sub)

                        else:
                            # Si no hay 'properties', procesarlo como un tipo simple
                            # Determinar si la referencia es 'mandatory' u 'optional'
                            #feature_type = 'mandatory' if prop in current_required else 'optional'
                            sanitized_ref = self.sanitize_name(ref_name.split('_')[-1]) # ref_name = self.sanitize_name(ref.split('/')[-1])
                            #ref_name = self.sanitize_name(ref.split('/')[-1])

                            # Agregar la referencia procesada como un tipo simple
                            feature['sub_features'].append({
                                'name': f"{full_name}_{sanitized_ref}", ## Error, si es una ref de un feature, tratar como subfeature (full_name + ref_name) // RefName Aparte {full_name}_{ref_name}
                                'type': 'mandatory', #mandatory no hay declaradas como optional
                                'description': ref_schema.get('description', ''),
                                'sub_features': [],
                                'type_data': 'Boolean' ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature
                            })
                            #print(f"Referencias simples detectadas: {ref}")

                    # Eliminar la referencia de la pila local al salir de esta rama
                    local_stack_refs.pop()

                # Procesar ítems en arreglos o propiedades adicionales
                elif 'items' in details:
                    items = details['items']
                    if '$ref' in items:
                        ref = items['$ref']
                        # Verificar si ya está en la pila local de la rama actual (es decir, un ciclo)
                        if ref in local_stack_refs:
                            print(f"*****Referencia cíclica detectada en items: {ref}. Saltando esta propiedad****")
                            continue

                        # Añadir la referencia a la pila local
                        local_stack_refs.append(ref)
                        ref_schema = self.resolve_reference(ref)

                        if ref_schema:
                            ## Linea no necesaria en esta implementacion: se usarian en omision de las refs (V_1.0)
                            ref_name = self.sanitize_name(ref.split('/')[-1])
                            #self.constraints.append(f"{full_name} => {ref_name}")
                            #feature_type = 'mandatory'

                            if 'properties' in ref_schema:
                                #sub_item_properties = ref_schema['properties']
                                #sub_item_required = ref_schema.get('required', [])
                                #sub_mandatory, sub_optional = self.parse_properties(sub_properties, sub_required, full_name, current_depth + 1, local_stack_refs) ## Otra manera de hacerlo
                                item_mandatory, item_optional = self.parse_properties(ref_schema['properties'], ref_schema.get('required', []), full_name, current_depth + 1, local_stack_refs)
                                feature['sub_features'].extend(item_mandatory + item_optional)
                            else:
                                # Si no hay 'properties', procesarlo como un tipo simple
                                feature_type = 'mandatory' if prop in current_required else 'optional' # Determinar si la referencia es 'mandatory' u 'optional'                                sanitized_ref = self.sanitize_name(ref_name.split('_')[-1]) # ref_name = self.sanitize_name(ref.split('/')[-1])
                                sanitized_ref = self.sanitize_name(ref_name.split('_')[-1]) # ref_name = self.sanitize_name(ref.split('/')[-1])

                                # Agregar la referencia procesada como un tipo simple
                                feature['sub_features'].append({
                                    'name': f"{full_name}_{sanitized_ref}", ## Error, si es una ref de un feature, tratar como subfeature (full_name + ref_name) // RefName Aparte {full_name}_{ref_name}
                                    'type': feature_type,
                                    'description': ref_schema.get('description', ''),
                                    'sub_features': [],
                                    'type_data': 'Boolean' ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature
                                })
                        # Eliminar la referencia de la pila local al salir de esta rama
                        local_stack_refs.pop()

                # Procesar propiedades adicionales
                elif 'additionalProperties' in details:
                    additional_properties = details['additionalProperties']
                    if '$ref' in additional_properties:
                        ref = additional_properties['$ref']
                        
                        # Verificar si ya está en la pila local de la rama actual (es decir, un ciclo)
                        if ref in local_stack_refs:
                            #print(f"*****Referencia cíclica detectada en additionalProperties: {ref}. Saltando esta propiedad****")
                            continue

                        # Añadir la referencia a la pila local
                        local_stack_refs.append(ref)
                        ref_schema = self.resolve_reference(ref)

                        if ref_schema:
                            ## Linea no necesaria en esta implementacion: se usarian en omision de las refs (V_1.0)
                            ref_name = self.sanitize_name(ref.split('/')[-1]) 
                            #self.constraints.append(f"{full_name} => {ref_name}")
                            #feature_type = 'mandatory'

                            if 'properties' in ref_schema:
                                item_mandatory, item_optional = self.parse_properties(ref_schema['properties'], [], full_name, current_depth + 1, local_stack_refs)
                                # ref_schema.get('required', []) se añade solo 1 linea mas al modelo ==> 1 mandatory unicamente
                                feature['sub_features'].extend(item_mandatory + item_optional)
                            elif 'oneOf' in ref_schema:
                                #feature_type = 'mandatory' if prop in current_required or is_required_by_description else 'optional'
                                oneOf_feature = self.process_oneOf(ref_schema['oneOf'], self.sanitize_name(f"{full_name}"), feature_type) #_{ref_oneOf}
                                feature_sub = oneOf_feature['sub_features']
                                # Agregar la referencia que contiene la caracteristica oneOf
                                feature['sub_features'].extend(feature_sub)
                            else:
                                # Si no hay 'properties', procesarlo como un tipo simple
                                feature_type = 'mandatory' if prop in current_required else 'optional' # Determinar si la referencia es 'mandatory' u 'optional'                                sanitized_ref = self.sanitize_name(ref_name.split('_')[-1]) # ref_name = self.sanitize_name(ref.split('/')[-1])
                                sanitized_ref = self.sanitize_name(ref_name.split('_')[-1]) # ref_name = self.sanitize_name(ref.split('/')[-1])

                                # Agregar la referencia procesada como un tipo simple
                                feature['sub_features'].append({
                                    'name': f"{full_name}_{sanitized_ref}", ## Error, si es una ref de un feature, tratar como subfeature (full_name + ref_name) // RefName Aparte {full_name}_{ref_name}
                                    'type': 'feature_type',
                                    'description': ref_schema.get('description', ''),
                                    'sub_features': [],
                                    'type_data': 'Boolean' ## Por defecto para la compatibilidad en los esquemas simples y la propiedad del feature
                                })

                        # Eliminar la referencia de la pila local al salir de esta rama
                        local_stack_refs.pop()

                # Extraer y añadir valores como subfeatures
                extracted_values = self.extract_values(description)

                if extracted_values:
                    for value in extracted_values:
                        feature['sub_features'].append({
                            'name': f"{full_name}_{value}",
                            'type': 'alternative',
                            'description': f"Specific value: {value}",
                            'sub_features': [],
                            'type_data': "String"  # Definir si obtener el tipo de dato o por defecto String
                        })

                # Procesar propiedades anidadas
                if 'properties' in details:
                    sub_properties = details['properties']
                    sub_required = details.get('required', [])
                    sub_mandatory, sub_optional = self.parse_properties(sub_properties, sub_required, full_name, current_depth + 1, local_stack_refs)
                    feature['sub_features'].extend(sub_mandatory + sub_optional)
                """
                else: ##Parte para definir las propiedades anidadas que son simples* Probar
                    sub_required = details.get('required', [])
                    sub_mandatory, sub_optional = self.parse_properties([], sub_required, full_name, current_depth + 1, local_stack_refs)
                    feature['sub_features'].extend(sub_mandatory + sub_optional)
                """    

                if feature_type == 'mandatory':
                    mandatory_features.append(feature)
                else:
                    optional_features.append(feature)

                self.processed_features.add(full_name)

        return mandatory_features, optional_features
            
    def save_descriptions(self, file_path):

        print(f"Saving descriptions to {file_path}...")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.descriptions, f, indent=4, ensure_ascii=False)
        print("Descriptions saved successfully.")

    def save_constraints(self, file_path):

        print(f"Saving constraints to {file_path}...")
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write("constraints\n" + "//Restricciones obtenidas de las referencias:\n") # Quitar para las pruebas con flamapy
            for constraint in self.constraints:
                f.write(f"\t{constraint}\n")
        print("Constraints saved successfully.")

def load_json_file(file_path):

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def properties_to_uvl(feature_list, indent=1):

    uvl_output = ""
    indent_str = '\t' * indent
    for feature in feature_list:
        type_str = f"{feature['type_data'].capitalize()} " if feature['type_data'] else "Boolean "
        if feature['sub_features']:
            uvl_output += f"{indent_str}{type_str}{feature['name']}\n"  # {type_str} opcional si se necesita
            # uvl_output += f"{indent_str}\t{feature['type']}\n" opcional si se necesita

            # Separar características obligatorias y opcionales
            sub_mandatory = [f for f in feature['sub_features'] if f['type'] == 'mandatory']
            sub_optional = [f for f in feature['sub_features'] if f['type'] == 'optional']
            sub_alternative = [f for f in feature['sub_features'] if f['type'] == 'alternative']

            if sub_mandatory:
                uvl_output += f"{indent_str}\tmandatory\n"
                uvl_output += properties_to_uvl(sub_mandatory, indent + 2)
            if sub_optional:
                uvl_output += f"{indent_str}\toptional\n"
                uvl_output += properties_to_uvl(sub_optional, indent + 2)
            if sub_alternative:
                uvl_output += f"{indent_str}\talternative\n"
                uvl_output += properties_to_uvl(sub_alternative, indent + 2)
        else:
            uvl_output += f"{indent_str}{type_str}{feature['name']}\n"  # {type_str} opcional si se necesita {{abstract}} 
    return uvl_output

def generate_uvl_from_definitions(definitions_file, output_file, descriptions_file):

    definitions = load_json_file(definitions_file) # Cargar el archivo de definiciones JSON
    processor = SchemaProcessor(definitions) # Inicializar el procesador de esquemas con las definiciones cargadas
    uvl_output = "namespace KubernetesTest1\nfeatures\n\tKubernetes {abstract}\n\t\toptional\n" # Iniciar la estructura base del archivo UVL {{abstract}}
    # Procesar cada definición en el archivo JSON
    for schema_name, schema in definitions.get('definitions', {}).items():
        root_schema = schema.get('properties', {})
        required = schema.get('required', [])
        type_str_feature = 'Boolean' ## Por defecto al no tener definido un tipo los features principales se les pone como Boolean
        #print(f"Processing schema: {schema_name}")
        mandatory_features, optional_features = processor.parse_properties(root_schema, required, processor.sanitize_name(schema_name)) # Obtener características obligatorias y opcionales
        
        # Agregar las características obligatorias y opcionales al archivo UVL
        if mandatory_features:
            uvl_output += f"\t\t\t{type_str_feature+' '}{processor.sanitize_name(schema_name)}\n" # {type_str_feature+' '} 
            uvl_output += f"\t\t\t\tmandatory\n"
            uvl_output += properties_to_uvl(mandatory_features, indent=5)

            if optional_features:
                uvl_output += f"\t\t\t\toptional\n"
                uvl_output += properties_to_uvl(optional_features, indent=5)
        elif optional_features:
            uvl_output += f"\t\t\t{type_str_feature+' '}{processor.sanitize_name(schema_name)}\n" # {type_str_feature+' '} 
            uvl_output += f"\t\t\t\toptional\n"
            uvl_output += properties_to_uvl(optional_features, indent=5)
        # Ajuste adicion esquemas simples
        if not root_schema: ## Para tener en cuenta los esquemas que no tienen propiedades: como los RawExtension, JSONSchemaPropsOrBool, JSONSchemaPropsOrArray que solo tienen descripcion
            if 'oneOf' in schema:
                #print(f"Procesando oneOf en {schema_name}")
                oneOf_feature = processor.process_oneOf(schema['oneOf'], processor.sanitize_name(schema_name), type_feature='optional')
                if oneOf_feature:
                    #uvl_output += f"\t\t\t{type_str_feature} {processor.sanitize_name(schema_name)}\n"
                    #uvl_output += f"\t\t\t\toptional\n"
                    #nameSubfeatures = oneOf_feature['sub_features']
                    uvl_output += properties_to_uvl([oneOf_feature], indent=3) ## Quizas cambiar la estructura general para las referencias a oneOf
                """
                    for nameSubfeature in nameSubfeatures:
                        names = nameSubfeature['name']
                        type_data = nameSubfeature['type_data']
                        if type_data == 'Number':
                            type_data = 'Integer'
                        uvl_output += f"\t\t\t\t\t{type_data} {names}\n"
                        print(names)
                """
            else:
                uvl_output += f"\t\t\t{type_str_feature+' '}{processor.sanitize_name(schema_name)}\n"
                #print("Schemas sin propiedades:",schema_name)
            #print(schema_name)
            #print(count2)

    # Guardar el archivo UVL generado
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(uvl_output)
    print(f"UVL output saved to {output_file}")

    # Guardar las descripciones extraídas
    processor.save_descriptions(descriptions_file)
    
    # Guardar las restricciones en el archivo UVL
    processor.save_constraints(output_file)

# Rutas de archivo relativas
#definitions_file = '../kubernetes-json-schema/v1.30.4/_definitions.json'
definitions_file = '../kubernetes-json-v1.30.2/v1.30.2/_definitions.json'
output_file = './kubernetes_combined_02.uvl'
descriptions_file = './descriptions_01.json'

# Generar archivo UVL y guardar descripciones
generate_uvl_from_definitions(definitions_file, output_file, descriptions_file)