## Relación entre los archivos de esta carpeta:

convert0.py genera 2 archivos: el feature model uvl en __kubernetes_combined_constraints.uvl__ y un conjunto de descripciones en __descriptions_01.json__. Este último es el que se usa en los análisis del script __analisisScriptNpl01.py__, para generar las constraints sobre los features y descripciones en __restrictions02.txt__. Todas las funciones que se mencionan en las agrupaciones se encuentran en [analisisScriptNpl01.py](https://github.com/CAOSD-group/fm-json-kubernetes/blob/main/scriptJsonToUvl/analisisScriptNpl01.py), así como los patrones y tratamiendo de las reglas y las palabras clave que añaden las descripciones al archivo descriptions_01.json en convert01.py.


# AGRUPACIONES DE LAS CONSTRAINTS SEGÚN EL MAPEO QUE TIENEN

Las agrupaciones en principio se separaron en 3 grupos: values, restrictions y dependencies. Por el momento se trabaja principalmente con el grupo restrictions. Este grupo formado por los patrones del script principal y localizado en [descriptions_01.json](https://github.com/CAOSD-group/fm-json-kubernetes/blob/main/scriptJsonToUvl/descriptions_01.json), guarda los features y filtra las descripciones con potencial a tener una constraint inhibida en el texto de la descripción. Los 3 grupos contienen los siguientes patrones:

- values: Agrupación de valores como extensiones del feature, valores concretos... se concentraban cualquier descripcion que contenga las palabras clave. Estos se integran principalmente en el script principal para añadir valores de los features _(valid|values are|supported)_
- restrictions: cualquier descripcion que contenga las palabras clave _(Note that this field cannot be set when|valid port number|must be in the range|must be greater than|Note that this field cannot be set when|are mutually exclusive properties|Must be set if type is|field MUST be empty if|must be non-empty if and only if|only if type|\. Required when|required when scope')_
- dependencies: Se encarga de buscar dependencias inhibidas en las descripciones

Mediante el análisis del fichero se obtienen las restricciones implementadas en el script de análisis, __analisisScriptNpl01.py__. Cada método implementado en ese script suele formar un conjunto sino muchos, relacionado de constraints desarrolladas para un patrón en común. 


### Constraints de referencias requires en relación al S.O de "os_name" y patrón _Note that this field..._

Esta agrupación se basa en las descripciones con palabras clave: _Note that this field cannot be set when_, todas las descripciones relacionadas mencionan un sistema operativo que si se usa, el feature no debería de ser seleccionado o up. Con el fragmento de _spec.os.name is windows_ se establece que S.O no tiene que ser seleccionado para que el feature este activo. El método que implementa este grupo es extract_constraints_os_name(), Las restricciones generadas tienen el formato siguiente:

io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_os_name_windows => !io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_securityContext_runAsUser
io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_os_name_linux => !io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_securityContext_windowsOptions
io_k8s_api_core_v1_PodSpec_os_name_windows => !io_k8s_api_core_v1_SecurityContext_allowPrivilegeEscalation
io_k8s_api_core_v1_PodSpec_os_name_windows => !io_k8s_api_core_v1_SecurityContext_appArmorProfile

Siendo todas del tipo Requires: feature_os_name => !feature_key. En total se generan 1247 restricciones de este tipo y se podría ampliar si se detecta otro conjunto grande relacionado con otra caracteristica de los esquemas tipo "spec.$otroValor...".


### Agrupación de constraints de intervalos y limites maximos y minimos

Esta agrupación se basa en las descripciones con palabras clave: _valid port number, must be in the range, must be greater than_. todas las descripciones relacionadas mencionan un número de puerto rango o limite de minimo y/o máximo. Al principio solo se trataba el primer patron de la agrupación pero el método diseñado _extractBounds_()_ maneja todos esos patrones obteniendo una gran variación de constraints. Maneja tanto las descripciones que contienen rangos como: "valid port number (1-65535, inclusive)", "valid port number, 0 < x < 65536.", "must be in the range 1 to 65535" o minimos simples como: "  Must be greater than zero.". Algunas de las restricciones obtenidas:

	io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_initContainers_lifecycle_preStop_tcpSocket_port => (io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_initContainers_lifecycle_preStop_tcpSocket_port_asInteger > 1 & io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_initContainers_lifecycle_preStop_tcpSocket_port_asInteger < 65535) | (io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_initContainers_lifecycle_preStop_tcpSocket_port_asString == 'IANA_SVC_NAME')
	io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_initContainers_livenessProbe_grpc_port > 1 & io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_initContainers_livenessProbe_grpc_port < 65535
	io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIService_spec_service_port > 1 & io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIService_spec_service_port < 65535

Un punto a destacar es que en la implementación de las reglas de rangos habían dos esquemas que en sus propiedades, concretamente _oneOf_, daba a elegir entre 2 tipos de datos, se aprovecho esto para generar 2 subfeatures dependiendo de los tipos de datos que habian en dicho esquema. Por lo tanto a la hora de resolver referencias como la siguiente: "Name or number of the port to access on the container. Number must be in the range 1 to 65535. Name must be an IANA_SVC_NAME.", se crearon 2 posibles opciones con alternative para seleccionar entre los tipos posibles de datos en el rango de los puertos, deduciendo para Integer o Number a _asInteger_ o _asNumber_ y para los nombres como _asString_ (queda pendiente ajustar el formato a 'IANA_SVC_NAME').

En total se generaron mas de 700 restricciones de tipo Integer y Boolean.

### Agrupación de restricciones valores que por defecto son mayor a cero y rangos en segundos:

En este caso se agrupan las constraints que por defecto o que su valor como número entero es mayor a cero. Este grupo forma parte de la anterior pero se disgrega para mostrarlo de manera individual, así se podria mostrar el mayor numero posible de estas descripciones y su variación. En este caso se tratan las descripciones que tienen el valor del mínimo como número entero o como nombre, en algunos casos se representaba el 0 como "zero" y se realizo una conversión entre esos valores para obtener un valor entero. Esta agrupación se encarga de manejar las expresiones como "must be greater than" o "less than or equal to", tratando así descripciones como "periodSeconds specifies the window of time for which the policy should hold true. PeriodSeconds must be greater than zero and less than or equal to 1800 (30 min)." o "value contains the amount of change which is permitted by the policy. It must be greater than zero".

Ejemplo de algunas reglas:
	io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIService_spec_versionPriority > 0
	io_k8s_api_autoscaling_v2_HPAScalingPolicy_periodSeconds > 0 & io_k8s_api_autoscaling_v2_HPAScalingPolicy_periodSeconds < 1801
	io_k8s_api_autoscaling_v2_HPAScalingPolicy_value > 0
	io_k8s_api_autoscaling_v2_HPAScalingRules_policies_periodSeconds > 0 & io_k8s_api_autoscaling_v2_HPAScalingRules_policies_periodSeconds < 1801
	io_k8s_api_autoscaling_v2_HPAScalingRules_policies_value > 0
	io_k8s_api_autoscaling_v2_HPAScalingRules_stabilizationWindowSeconds > 0 & io_k8s_api_autoscaling_v2_HPAScalingRules_stabilizationWindowSeconds < 3601
	[...]

### Agrupación de restricciones de exclusión mutua:

Esta agrupación se basa en las descripciones con palabras clave: _vare mutually exclusive properties_. Todas las descripciones relacionadas mencionan una exclusión entre propiedades de un feature. En este caso no es un grupo muy grande pero si visible, son 24 descripciones pero se obtienen unicamente 12 constraints, esto se debe a que en todas el texto es el mismo y se habla ya de las 2 propiedades, por lo que sobre 12 descripciones ya se pueden obtener el total de las reglas que involucren a los 2 features. Las descripciones que maneja la función extract_constraints_mutualy_exclusive() son: "name is the name of the resource being referenced.\n\nOne of `name` or `selector` must be set, but `name` and `selector` are mutually exclusive properties. If one is set, the other must be unset.",
Algunas de las restricciones obtenidas:

	(io_k8s_api_admissionregistration_v1_ParamRef_name => !io_k8s_api_admissionregistration_v1_ParamRef_selector) & (io_k8s_api_admissionregistration_v1_ParamRef_selector => !io_k8s_api_admissionregistration_v1_ParamRef_name)
	(io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBinding_spec_paramRef_name => !io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBinding_spec_paramRef_selector) & (io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBinding_spec_paramRef_selector => !io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBinding_spec_paramRef_name)
	(io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingList_items_spec_paramRef_name => !io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingList_items_spec_paramRef_selector) & (io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingList_items_spec_paramRef_selector => !io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingList_items_spec_paramRef_name)
	(io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingSpec_paramRef_name => !io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingSpec_paramRef_selector) & (io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingSpec_paramRef_selector => !io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingSpec_paramRef_name)

Como se puede ver, todas las restricciones son relacionadas a "name" y "selector", propiedades que no pueden ser seleccionadas a la vez. Para ello se especifico en las reglas que si una esta up la otra tiene que no estar activa... En total se generan 12 restricciones de tipo Boolean (Pendiente añadir a cada Boolean un hijo con tipo String o refs)

### Agrupación de restricciones que se seleccionan si uno de los tipos coincide con la propiedad del esquema:

Esta agrupación se basa en las descripciones con palabras clave: _only if type is_, _Must be set if type is_, _must be non-empty if and only if_. Todas las descripciones relacionadas mencionan un valor de la propiedad "type" que debe ser escogido para que la propiedad en cuestión deba de ser configurada. "type" es una propiedad del esquema que representa el valor o tipo del esquema que puede ser, la propiedad en cuestión o localhostProfile es el sub-feature que depende del valor que tome "type". Solo si es el valor indicado en la descripción será configurado y no otro. Una de las descripciones que se tratan en la función extract_constraints_if es la siguiente: _"localhostProfile indicates a profile loaded on the node that should be used. The profile must be preconfigured on the node to work. Must match the loaded name of the profile. Must be set if and only if type is \"Localhost\"."_, relacionada con el primer patrón, _"localhostProfile indicates a profile defined in a file on the node should be used. The profile must be preconfigured on the node to work. Must be a descending path, relative to the kubelet's configured seccomp profile location. Must be set if type is \"Localhost\".Must NOT be set for any other type.",_ relacionado con el segundo patrón. Algunas de las restricciones obtenidas en relación a esas descripcciones son:

	io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_securityContext_appArmorProfile_type_Localhost => io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_securityContext_appArmorProfile_localhostProfile
	io_k8s_api_core_v1_PodTemplateSpec_spec_securityContext_seccompProfile_type_Localhost => io_k8s_api_core_v1_PodTemplateSpec_spec_securityContext_seccompProfile_localhostProfile
	io_k8s_api_core_v1_SecurityContext_seccompProfile_type_Localhost => io_k8s_api_core_v1_SecurityContext_seccompProfile_localhostProfile
	io_k8s_api_flowcontrol_v1_PriorityLevelConfiguration_spec_type_Limited => io_k8s_api_flowcontrol_v1_PriorityLevelConfiguration_spec_limited

En la función que trata el patron y las restricciones correspondientes también se tratan otros conjuntos de restricciones diferenciandolos por el nombre del feature y entre fragmentos del texto de la descripción. El tratamiento en general es el mismo (obtención del valor requerido) pero varía en cuanto a la implementación de la regla. Por ello, el anterior caso se basa en obtener el único valor y si el valor es ese, el sub-feature estará activo. Por otro lado, en cuanto a la variación de las constraints, este es el otro tipo que se trata por el momento, relacionado con el patrón _field MUST be empty if_, en que en la descripción se especifica que si el valor seleccionado es "Limited" este sub-feature tiene que ser "empty" o false en este caso, solo estará seleccionado si el valor del tipo es "Exempt". La descripción que trata es: _"`exempt` specifies how requests are handled for an exempt priority level. This field MUST be empty if `type` is `\"Limited\"`. This field MAY be non-empty if `type` is `\"Exempt\"`. If empty and `type` is `\"Exempt\"` then the default values for `ExemptPriorityLevelConfiguration` apply.",_. Algunas de las restricciones obtenidas son:

	(io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationList_items_spec_type_Limited => !io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationList_items_spec_exempt) | (io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationList_items_spec_type_Exempt => io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationList_items_spec_exempt)
	(io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationList_items_spec_type_Limited => !io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationList_items_spec_exempt) | (io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationList_items_spec_type_Exempt => io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationList_items_spec_exempt)

En total se generaron mas de 300 restricciones de tipo Boolean.

### Agrupación de restricciones Required when

Esta agrupación se basa en las descripciones con palabras clave: _\. Required when_ y _required when scope_, todas las descripciones relacionadas mencionan un valor de una propiedad que si se usa, la propiedad debería de ser seleccionado. El tratamiento en general es similar a la anterior agrupación (obtención del valor requerido) pero varía en cuanto a los términos y la implementación. Este fue el primer grupo con el que se trabajo en cuando a valores de propiedadades. Las descripciones sobre las que se trabaja son las siguientes: _"namespace is the namespace of the resource being referenced. This field is required when scope is set to \"Namespace\" and must be unset when scope is set to \"Cluster\"."_, de la que se extrae el segundo tipo con una restricción con _or_, y la otra descripción: _"webhook describes how to call the conversion webhook. Required when `strategy` is set to `\"Webhook\"`."_, de la que se extrae la primera restricción simple.

	io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_CustomResourceConversion_strategy_Webhook => io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_CustomResourceConversion_webhook
	io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_CustomResourceDefinitionSpec_conversion_strategy_Webhook => io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_CustomResourceDefinitionSpec_conversion_webhook
	io_k8s_api_networking_v1_IngressClass_spec_parameters_scope_Namespace => io_k8s_api_networking_v1_IngressClass_spec_parameters_namespace & !(io_k8s_api_networking_v1_IngressClass_spec_parameters_scope_Cluster)
	io_k8s_api_networking_v1_IngressClassList_items_spec_parameters_scope_Namespace => io_k8s_api_networking_v1_IngressClassList_items_spec_parameters_namespace & !(io_k8s_api_networking_v1_IngressClassList_items_spec_parameters_scope_Cluster)

En total se generan 8 restricciones de este tipo.


### Agrupación de restricciones $... :

En desarrollo de más patrones y constraints...



### Archivo en Agrupaciones.md