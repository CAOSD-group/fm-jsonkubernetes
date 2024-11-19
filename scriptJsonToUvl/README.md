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

Esta agrupación se basa en las descripciones con palabras clave: _valid port number, must be in the range, must be greater than_. todas las descripciones relacionadas mencionan un número de puerto rango o limite de minimo y/o máximo. Al principio solo se trataba el primer patron de la agrupación pero el método diseñado extractBounds() maneja todos esos patrones obteniendo una gran variación de constraints. Maneja tanto las descripciones que contienen rangos como: "valid port number (1-65535, inclusive)", "valid port number, 0 < x < 65536.", "must be in the range 1 to 65535" o minimos simples como: "  Must be greater than zero.". Algunas de las restricciones obtenidas:

	io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_initContainers_lifecycle_preStop_tcpSocket_port => (io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_initContainers_lifecycle_preStop_tcpSocket_port_asInteger > 1 & io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_initContainers_lifecycle_preStop_tcpSocket_port_asInteger < 65535) | (io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_initContainers_lifecycle_preStop_tcpSocket_port_asString == 'IANA_SVC_NAME')
	io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_initContainers_livenessProbe_grpc_port > 1 & io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_initContainers_livenessProbe_grpc_port < 65535
	io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIService_spec_service_port > 1 & io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIService_spec_service_port < 65535

Un punto a destacar es que en la implementación de las reglas de rangos habían dos esquemas que en sus propiedades, concretamente _oneOf_, daba a elegir entre 2 tipos de datos, se aprovecho esto para generar 2 subfeatures dependiendo de los tipos de datos que habian en dicho esquema. Por lo tanto a la hora de resolver referencias como la siguiente: "Name or number of the port to access on the container. Number must be in the range 1 to 65535. Name must be an IANA_SVC_NAME.", se crearon 2 posibles opciones con alternative para seleccionar entre los tipos posibles de datos en el rango de los puertos, deduciendo para Integer o Number a _asInteger_ o _asNumber_ y para los nombres como _asString_ (queda pendiente ajustar el formato a 'IANA_SVC_NAME').

En total se generaron mas de 700 restricciones de tipo Integer y Boolean.

Adición de un nuevo grupo "must be between". Son nuevas restricciones con intervalos de 1-30 segundos y 0-100. Seguidos por el siguiente patron y similar a la funcionalidad ya propuesta:
    between_text_pattern = re.compile(r'must\s+be\s+between\s+(\d+)\s+and\s+(\d+)', re.IGNORECASE)

En total se agregaron 22 restricciones nuevas de este tipo.


### Agrupación de restricciones valores que por defecto son mayor a cero y rangos en segundos:

En este caso se agrupan las constraints que por defecto o que su valor como número entero es mayor a cero. Este grupo forma parte de la anterior pero se disgrega para mostrarlo de manera individual, así se podria mostrar el mayor numero posible de estas descripciones y su variación. En este caso se tratan las descripciones que tienen el valor del mínimo como número entero o como nombre, en algunos casos se representaba el 0 como "zero" y se realizo una conversión entre esos valores para obtener un valor entero. Esta agrupación se encarga de manejar las expresiones como "must be greater than" o "less than or equal to", tratando así descripciones como "periodSeconds specifies the window of time for which the policy should hold true. PeriodSeconds must be greater than zero and less than or equal to 1800 (30 min)." o "value contains the amount of change which is permitted by the policy. It must be greater than zero". Ejemplo de algunas reglas:

	io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIService_spec_versionPriority > 0
	io_k8s_api_autoscaling_v2_HPAScalingPolicy_periodSeconds > 0 & io_k8s_api_autoscaling_v2_HPAScalingPolicy_periodSeconds < 1801
	io_k8s_api_autoscaling_v2_HPAScalingPolicy_value > 0
	io_k8s_api_autoscaling_v2_HPAScalingRules_policies_periodSeconds > 0 & io_k8s_api_autoscaling_v2_HPAScalingRules_policies_periodSeconds < 1801
	io_k8s_api_autoscaling_v2_HPAScalingRules_policies_value > 0
	io_k8s_api_autoscaling_v2_HPAScalingRules_stabilizationWindowSeconds > 0 & io_k8s_api_autoscaling_v2_HPAScalingRules_stabilizationWindowSeconds < 3601


### Agrupación de restricciones de exclusión mutua:

Esta agrupación se basa en las descripciones con palabras clave: _vare mutually exclusive properties_. Todas las descripciones relacionadas mencionan una exclusión entre propiedades de un feature. En este caso no es un grupo muy grande pero si visible, son 24 descripciones pero se obtienen unicamente 12 constraints, esto se debe a que en todas el texto es el mismo y se habla ya de las 2 propiedades, por lo que sobre 12 descripciones ya se pueden obtener el total de las reglas que involucren a los 2 features. Las descripciones que maneja la función extract_constraints_mutualy_exclusive() son: "name is the name of the resource being referenced.\n\nOne of `name` or `selector` must be set, but `name` and `selector` are mutually exclusive properties. If one is set, the other must be unset.", algunas de las restricciones obtenidas:

	(io_k8s_api_admissionregistration_v1_ParamRef_name => !io_k8s_api_admissionregistration_v1_ParamRef_selector) & (io_k8s_api_admissionregistration_v1_ParamRef_selector => !io_k8s_api_admissionregistration_v1_ParamRef_name)
	(io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBinding_spec_paramRef_name => !io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBinding_spec_paramRef_selector) & (io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBinding_spec_paramRef_selector => !io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBinding_spec_paramRef_name)
	(io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingList_items_spec_paramRef_name => !io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingList_items_spec_paramRef_selector) & (io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingList_items_spec_paramRef_selector => !io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingList_items_spec_paramRef_name)
	(io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingSpec_paramRef_name => !io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingSpec_paramRef_selector) & (io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingSpec_paramRef_selector => !io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicyBindingSpec_paramRef_name)

Como se puede ver, todas las restricciones son relacionadas a "name" y "selector", propiedades que no pueden ser seleccionadas a la vez. Para ello se especifico en las reglas que si una esta up la otra tiene que no estar activa... En total se generan 12 restricciones de tipo Boolean (Pendiente añadir a cada Boolean un hijo con tipo String o refs)

### Agrupación de restricciones que se seleccionan si uno de los tipos coincide con la propiedad del esquema:

Esta agrupación se basa en las descripciones con palabras clave: _only if type is_, _Must be set if type is_, _must be non-empty if and only if_. Todas las descripciones relacionadas mencionan un valor de la propiedad "type" que debe ser escogido para que la propiedad en cuestión deba de ser configurada. "type" es una propiedad del esquema que representa el valor o tipo del esquema que puede ser, la propiedad en cuestión o localhostProfile es el sub-feature que depende del valor que tome "type". Solo si es el valor indicado en la descripción será configurado y no otro. Una de las descripciones que se tratan en la función extract_constraints_if() es la siguiente: _"localhostProfile indicates a profile loaded on the node that should be used. The profile must be preconfigured on the node to work. Must match the loaded name of the profile. Must be set if and only if type is \"Localhost\"."_, relacionada con el primer patrón, _"localhostProfile indicates a profile defined in a file on the node should be used. The profile must be preconfigured on the node to work. Must be a descending path, relative to the kubelet's configured seccomp profile location. Must be set if type is \"Localhost\".Must NOT be set for any other type.",_ relacionado con el segundo patrón. Algunas de las restricciones obtenidas en relación a esas descripcciones son:

	io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_securityContext_appArmorProfile_type_Localhost => io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_securityContext_appArmorProfile_localhostProfile
	io_k8s_api_core_v1_PodTemplateSpec_spec_securityContext_seccompProfile_type_Localhost => io_k8s_api_core_v1_PodTemplateSpec_spec_securityContext_seccompProfile_localhostProfile
	io_k8s_api_core_v1_SecurityContext_seccompProfile_type_Localhost => io_k8s_api_core_v1_SecurityContext_seccompProfile_localhostProfile
	io_k8s_api_flowcontrol_v1_PriorityLevelConfiguration_spec_type_Limited => io_k8s_api_flowcontrol_v1_PriorityLevelConfiguration_spec_limited

En la función que trata el patron y las restricciones correspondientes también se tratan otros conjuntos de restricciones diferenciandolos por el nombre del feature y entre fragmentos del texto de la descripción. El tratamiento en general es el mismo (obtención del valor requerido) pero varía en cuanto a la implementación de la regla. Por ello, el anterior caso se basa en obtener el único valor y si el valor es ese, el sub-feature estará activo. Por otro lado, en cuanto a la variación de las constraints, este es el otro tipo que se trata por el momento, relacionado con el patrón _field MUST be empty if_, en que en la descripción se especifica que si el valor seleccionado es "Limited" este sub-feature tiene que ser "empty" o false en este caso, solo estará seleccionado si el valor del tipo es "Exempt". La descripción que trata es: _"`exempt` specifies how requests are handled for an exempt priority level. This field MUST be empty if `type` is `\"Limited\"`. This field MAY be non-empty if `type` is `\"Exempt\"`. If empty and `type` is `\"Exempt\"` then the default values for `ExemptPriorityLevelConfiguration` apply.",_. Algunas de las restricciones obtenidas son:

	(io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationList_items_spec_type_Limited => !io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationList_items_spec_exempt) | (io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationList_items_spec_type_Exempt => io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationList_items_spec_exempt)
	(io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationSpec_type_Limited => !io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationSpec_exempt) | (io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationSpec_type_Exempt => io_k8s_api_flowcontrol_v1_PriorityLevelConfigurationSpec_exempt)
	(io_k8s_api_flowcontrol_v1beta3_PriorityLevelConfiguration_spec_type_Limited => !io_k8s_api_flowcontrol_v1beta3_PriorityLevelConfiguration_spec_exempt) | (io_k8s_api_flowcontrol_v1beta3_PriorityLevelConfiguration_spec_type_Exempt => io_k8s_api_flowcontrol_v1beta3_PriorityLevelConfiguration_spec_exempt)

En total se generaron mas de 300 restricciones de tipo Boolean.

### Agrupación de restricciones Required when

Esta agrupación se basa en las descripciones con palabras clave: _\. Required when_ y _required when scope_, todas las descripciones relacionadas mencionan un valor de una propiedad que si se usa, la propiedad debería de ser seleccionado. El tratamiento en general es similar a la anterior agrupación (obtención del valor requerido) pero varía en cuanto a los términos y la implementación. Este fue el primer grupo con el que se trabajo en cuando a valores de propiedadades. Las descripciones sobre las que se trabaja son las siguientes: _"namespace is the namespace of the resource being referenced. This field is required when scope is set to \"Namespace\" and must be unset when scope is set to \"Cluster\"."_, de la que se extrae el segundo tipo con una restricción con _or_, y la otra descripción: _"webhook describes how to call the conversion webhook. Required when `strategy` is set to `\"Webhook\"`."_, de la que se extrae la primera restricción simple. Estas son algunas de las restricciones obtenidas:

	io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_CustomResourceConversion_strategy_Webhook => io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_CustomResourceConversion_webhook
	io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_CustomResourceDefinitionSpec_conversion_strategy_Webhook => io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_CustomResourceDefinitionSpec_conversion_webhook
	io_k8s_api_networking_v1_IngressClass_spec_parameters_scope_Namespace => io_k8s_api_networking_v1_IngressClass_spec_parameters_namespace & !(io_k8s_api_networking_v1_IngressClass_spec_parameters_scope_Cluster)
	io_k8s_api_networking_v1_IngressClassList_items_spec_parameters_scope_Namespace => io_k8s_api_networking_v1_IngressClassList_items_spec_parameters_namespace & !(io_k8s_api_networking_v1_IngressClassList_items_spec_parameters_scope_Cluster)

En total se generan 8 restricciones de este tipo.



### Agrupación de restricciones If the operator

Esta agrupación se basa en las descripciones con palabras clave: _If the operator is_, todas las descripciones relacionadas mencionan en 2 casos varios pares de valores que si se seleccionan encadenan a otro feature a que se seleccione. Por otro lado, hay un caso aislado donde se menciona solo un posible valor para realizar la dependencia. El tratamiento en general es similar en todos los casos por las palabras clave pero se obtienen mas o menos dependiendo de la descripcción. Las descripciones sobre las que se trabaja son las siguientes: _"values is an array of string values. If the operator is In or NotIn, the values array must be non-empty. If the operator is Exists or DoesNotExist, the values array must be empty. This array is replaced during a strategic merge patch.",_, o la del caso único: _"Value is the taint value the toleration matches to. If the operator is Exists, the value should be empty, otherwise just a regular string.",_ . La función que desarrolla estas constraints es extract_constraints_operator(). Estas son algunas de las restricciones obtenidas:

1	(io_k8s_api_core_v1_ScopedResourceSelectorRequirement_operator_In | io_k8s_api_core_v1_ScopedResourceSelectorRequirement_operator_NotIn => 				   
	io_k8s_api_core_v1_ScopedResourceSelectorRequirement_values) | (io_k8s_api_core_v1_ScopedResourceSelectorRequirement_operator_Exists |io_k8s_api_core_v1_ScopedResourceSelectorRequirement_operator_DoesNotExist => !io_k8s_api_core_v1_ScopedResourceSelectorRequirement_values)
2	io_k8s_api_core_v1_Toleration_operator_Exists => io_k8s_api_core_v1_Toleration_value
3	(io_k8s_api_core_v1_TopologySpreadConstraint_labelSelector_matchExpressions_operator_In
	io_k8s_api_core_v1_TopologySpreadConstraint_labelSelector_matchExpressions_operator_NotIn => io_k8s_api_core_v1_TopologySpreadConstraint_labelSelector_matchExpressions_values) | (io_k8s_api_core_v1_TopologySpreadConstraint_labelSelector_matchExpressions_operator_Exists |io_k8s_api_core_v1_TopologySpreadConstraint_labelSelector_matchExpressions_operator_DoesNotExist => !io_k8s_api_core_v1_TopologySpreadConstraint_labelSelector_matchExpressions_values)

En total se agregaron 701 restricciones.


### Agrupacion de restricciones least one

Función que extrae las restricciones de las descripciones que contienen _Exactly one of_, _a least one of_, _at least one of_, basadas en la condición de que al menos un feature debe de ser seleccionado. La función donde se implementa el tratamiento es en extract_constraints_least_one(). En esta función se usan varias expresiones con las palabras clave mencionadas para dividir los casos y separar la formación de las constraints en distintas partes de la función. La descripción del primer grupo se expecifica que solo uno de los 2 tipos debe de ser especificado:_"url gives the location of the webhook, in standard URL form (`scheme://host:port/path`). Exactly one of `url` or `service` must be specified.\n\nThe `host` should not refer to a service running in the cluster; use the `service` field instead. The host might be resolved via external DNS in some apiservers (e.g., `kube-apiserver` cannot resolve in-cluster DNS as that would be a layering violation). `host`..."_, de aquí se deduce que exactamente solo 1 de las propidades es seleccionada. Por otro lado, las restantes relacionadas con a/at least one mencionan en sus descripciones que al menos una de las propiedades debe de ser seleccionado, dando a entender que las 2 pueden ser usadas. 

Primer grupo:
	io_k8s_api_admissionregistration_v1alpha1_ValidatingAdmissionPolicySpec_validations | io_k8s_api_admissionregistration_v1alpha1_ValidatingAdmissionPolicySpec_auditAnnotations
	io_k8s_api_admissionregistration_v1beta1_ValidatingAdmissionPolicy_spec_validations | io_k8s_api_admissionregistration_v1beta1_ValidatingAdmissionPolicy_spec_auditAnnotations
	io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicySpec_validations | io_k8s_api_admissionregistration_v1_ValidatingAdmissionPolicySpec_auditAnnotations

Segundo grupo:
	io_k8s_api_admissionregistration_v1_ValidatingWebhook_clientConfig_url | io_k8s_api_admissionregistration_v1_ValidatingWebhook_clientConfig_service
	io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_WebhookClientConfig_url | io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_WebhookClientConfig_serviceç

Tercer grupo de la expresión:
	io_k8s_api_batch_v1_SuccessPolicy_rules_succeededIndexes | io_k8s_api_batch_v1_SuccessPolicy_rules_succeededCount
	io_k8s_api_batch_v1_SuccessPolicyRule_succeededIndexes | io_k8s_api_batch_v1_SuccessPolicyRule_succeededCount

En total hay XX constraints.

### Agrupacion de restricciones primary or
#### one of

Esta agrupación se basa en las descripciones con palabras clave: _non-resource access request_, _succeededIndexes specifies_, _Represents the requirement on the container_, _ResourceClaim object in the same namespace as this pod_. Esta función, extract_constraints_primary_or(), se caracteriza en que no usa patrones para extraer los valores de las descripciones ya que no estan inhibidas en las que se usan como clave. Se empezó analizando las restricciones de las descripciones que contienen "Exactly one of" en las descripciones generales(principales) de los features. Sin embargo, el script principal no esta diseñado para coger descripciones de primer nivel (y añadirlas a descriptions_01.json) por evitar incongruencias. Por ese motivo, se realizan las inserciones de las constraints de manera más especifica usando las descripciones, palabras y nombres de los features para obtener los features involucrados en las descripciones mencionadas en el primer nivel. Es decir, no se usa la descripción principal pero mediante las descripciones de las propiedades se obtienen los valores necesarios. En su mayoría las restricciones suelen ser del mismo tipo: "feature1 or feature2". Por lo que, con obtener uno de los 2 features relacionados se puede añadir el otro añadiendolo directamente. El primer grupo formado se baso en la descripción principal: _"SelfSubjectAccessReviewSpec is a description of the access request. Exactly one of ResourceAuthorizationAttributes and NonResourceAuthorizationAttributes must be set"_, de aquí se dedujo que solo una de las 2 propiedades puede ser seleccionada. En general y precedidas por _one of_ las descripciones usadas en esta agrupación y siguientes se basa en la aparición de _one of_. 

Otra descripción relacionada con el segundo grupo, _"SuccessPolicyRule describes rule for declaring a Job as succeeded. Each rule must have at least one of the \"succeededIndexes\" or \"succeededCount\" specified."_. Se interpreto como que al menos uno de las 2 propiedades tenga que estar activa por lo que se añadio mediante un or simplemente quedando similar a: feature1 or feature2. Repitiendo el mismo patrón que el primer grupo, en la tercera descripción y cuarta la interpretación es la misma. Dando como resultado restricciones de tipo: feature1 XOR feature2. Descripción del tercer grupo: _"PodFailurePolicyRule describes how a pod failure is handled when the requirements are met. One of onExitCodes and onPodConditions, but not both, can be used in each rule."_, cuarto grupo: _"ClaimSource describes a reference to a ResourceClaim.\n\nExactly one of these fields should be set.  Consumers of this type must treat an empty object as if it has an unknown value."_.

Algunas de las descripciones obtenidas son las siguientes:
Primer grupo, 8 restricciones en total:
	(io_k8s_api_authorization_v1_SelfSubjectAccessReview_spec_nonResourceAttributes | io_k8s_api_authorization_v1_SelfSubjectAccessReview_spec_resourceAttributes) & 
	!(io_k8s_api_authorization_v1_SelfSubjectAccessReview_spec_nonResourceAttributes | io_k8s_api_authorization_v1_SelfSubjectAccessReview_spec_resourceAttributes)
	(io_k8s_api_authorization_v1_SelfSubjectAccessReviewSpec_nonResourceAttributes | io_k8s_api_authorization_v1_SelfSubjectAccessReviewSpec_resourceAttributes) &
	!(io_k8s_api_authorization_v1_SelfSubjectAccessReviewSpec_nonResourceAttributes | io_k8s_api_authorization_v1_SelfSubjectAccessReviewSpec_resourceAttributes)

Segundo grupo, 9 restricciones en total:
	io_k8s_api_batch_v1_SuccessPolicy_rules_succeededIndexes | io_k8s_api_batch_v1_SuccessPolicy_rules_succeededCount
	io_k8s_api_batch_v1_SuccessPolicyRule_succeededIndexes | io_k8s_api_batch_v1_SuccessPolicyRule_succeededCount

Tercer grupo, 9 restricciones en total:
	(io_k8s_api_batch_v1_PodFailurePolicy_rules_onExitCodes | io_k8s_api_batch_v1_PodFailurePolicy_rules_onPodConditions) & !(io_k8s_api_batch_v1_PodFailurePolicy_rules_onExitCodes & io_k8s_api_batch_v1_PodFailurePolicy_rules_onPodConditions)
	(io_k8s_api_batch_v1_PodFailurePolicyRule_onExitCodes | io_k8s_api_batch_v1_PodFailurePolicyRule_onPodConditions) & !(io_k8s_api_batch_v1_PodFailurePolicyRule_onExitCodes & io_k8s_api_batch_v1_PodFailurePolicyRule_onPodConditions)

Cuarto grupo, 30 restricciones en total:
	(io_k8s_api_core_v1_ReplicationControllerList_items_spec_template_spec_resourceClaims_source_resourceClaimName | io_k8s_api_core_v1_ReplicationControllerList_items_spec_template_spec_resourceClaims_source_resourceClaimTemplateName) & !(io_k8s_api_core_v1_ReplicationControllerList_items_spec_template_spec_resourceClaims_source_resourceClaimName & io_k8s_api_core_v1_ReplicationControllerList_items_spec_template_spec_resourceClaims_source_resourceClaimTemplateName)
	(io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_resourceClaims_source_resourceClaimName | io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_resourceClaims_source_resourceClaimTemplateName) & !(io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_resourceClaims_source_resourceClaimName & io_k8s_api_core_v1_ReplicationControllerSpec_template_spec_resourceClaims_source_resourceClaimTemplateName)

Nuevo conjunto añadido "datasetUUID is", 37 nuevas constraints en total. 
probar con el modelo correspondiente...

### Agrupacion de restricciones complejas

En esta parte se agregan las restricciones "complejas", son largas y contienen varios operadores lógicos o featues involucrados. Se implementan en la función extract_constraints_multiple_conditions(). Esta agrupación se basa en las descripciones con palabras clave: _conditions may not be_, _Details about a waiting_, las restricciones se dividen en diferentes casos por las palabras clave mencionadas. Asi que cada expresion tendrá una funcionalidad totalemente diferente. En el primer caso se usan patrones para obtener los diferentes valores de los features que se van a usar y el objetivo es definir los posibles valores que un feature no tiene que seleccionar. La descripciones que se analizan son: _"status of the condition, one of True, False, Unknown. Approved, Denied, and Failed conditions may not be \"False\" or \"Unknown\"."_. Siendo _False_ y _Unknown_ los estados que las condiciones de tipo _Approved_, _Denied_ y _Failed_ no pueden escogerse. En el otro caso se agregan los posibles valores de los features manualmente ya que no hay una descripción donde se mencionen, al ser los mismos en las descripciones no hay problema en agregarlos de esa manera. Aquí como en el anterior caso, se basa en definir los features que no se pueden seleccionar o seleccionar en relación con los otros features. En base a la siguiente descripción general: _"ContainerState holds a possible state of container. Only one of its members may be specified. If none of them is specified, the default one is ContainerStateWaiting."_, se dedujo que una de las propiedades del esquema debia de ser seleccionada, y si una era seleccionada las otras no se podían seleccionar. Además de que si ninguna esta seleccionada se deja por defecto _ContainerStateWaiting_. Esto se tradujo a las siguientes representaciones:
	Exclusividad: Solo un estado a la vez
	(featureWaiting => !featureRunning & !featureTerminated)
	& (featureRunning => !featureStateWaiting & !featureStateTerminated)
	& (featureTerminated => !featureStateWaiting & !featureStateRunning)
	Valor por defecto: Si ninguno está seleccionado, se asume ContainerStateWaiting
	!featureRunning & !featureTerminated => featureWaiting

Mediante estos grupos de restricciones se generaron las siguientes:
En total se generaron 4 restricciones del siguiente grupo:

	(io_k8s_api_certificates_v1_CertificateSigningRequest_status_conditions_type_Approved => !io_k8s_api_certificates_v1_CertificateSigningRequest_status_conditions_status_False & !io_k8s_api_certificates_v1_CertificateSigningRequest_status_conditions_status_Unknown)
	(io_k8s_api_certificates_v1_CertificateSigningRequest_status_conditions_type_Denied => !io_k8s_api_certificates_v1_CertificateSigningRequest_status_conditions_status_False & !io_k8s_api_certificates_v1_CertificateSigningRequest_status_conditions_status_Unknown)
	(io_k8s_api_certificates_v1_CertificateSigningRequest_status_conditions_type_Failed => !io_k8s_api_certificates_v1_CertificateSigningRequest_status_conditions_status_False & !io_k8s_api_certificates_v1_CertificateSigningRequest_status_conditions_status_Unknown)

En total se generaron 21 del segundo grupo:

	(io_k8s_api_core_v1_PodList_items_status_containerStatuses_lastState_waiting => !io_k8s_api_core_v1_PodList_items_status_containerStatuses_lastState_running & !io_k8s_api_core_v1_PodList_items_status_containerStatuses_lastState_terminated) & (io_k8s_api_core_v1_PodList_items_status_containerStatuses_lastState_running => !io_k8s_api_core_v1_PodList_items_status_containerStatuses_lastState_waiting & !io_k8s_api_core_v1_PodList_items_status_containerStatuses_lastState_terminated) & (io_k8s_api_core_v1_PodList_items_status_containerStatuses_lastState_terminated => !io_k8s_api_core_v1_PodList_items_status_containerStatuses_lastState_waiting & !io_k8s_api_core_v1_PodList_items_status_containerStatuses_lastState_running)& (!io_k8s_api_core_v1_PodList_items_status_containerStatuses_lastState_running &!io_k8s_api_core_v1_PodList_items_status_containerStatuses_lastState_terminated => io_k8s_api_core_v1_PodList_items_status_containerStatuses_lastState_waiting)

** Nuevo conjunto agregado "Sleep represents" con 175 constraints nuevas. Basada en una descripción principal y que solo permite seleccionar un único feature de sus propiedades e ignora otra que esta en estado _deprecated_.
	(io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_lifecycle_postStart_exec | io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_lifecycle_postStart_httpGet | io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_lifecycle_postStart_sleep) & !(io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_lifecycle_postStart_exec & io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_lifecycle_postStart_httpGet) & !(io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_lifecycle_postStart_exec & io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_lifecycle_postStart_sleep) & !(io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_lifecycle_postStart_httpGet & io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_lifecycle_postStart_sleep) & !io_k8s_api_apps_v1_DaemonSet_spec_template_spec_containers_lifecycle_postStart_tcpSocket
	


### Agrupacion de restricciones de las politicas de reinicio que se permiten en relación a las plantillas que define un feature

Genera restricciones UVL para template.spec.restartPolicy basadas basadas en los valores que se permiten segun las descripciones. Se agregan las restricciones de politicas de reinicio, se basan en la definición del valor que da "template.spec.restartPolicy". Maneja dos casos: Un único valor permitido: "Always". Dos valores permitidos: "Never" o "OnFailure". Se implementan en la función extract_constraints_template_onlyAllowed(). Las restricciones se dividen en dos casos por las palabras clave _value is_ y _values are_. Diferenciandose en que en el primer caso solo hay un valor permitido y en el segundo 2 valores. En base a las siguientes descripciones: _... The only allowed template.spec.restartPolicy value is \"Always\"._, siendo el primer caso y dando por hecho que el único valor posible es Always (evitando seleccionar los otros 2). Por otro lado, la otra descripción: _...The only allowed template.spec.restartPolicy values are \"Never\" or \"OnFailure\"_, deduciendo que los valores posibles son _Never_ y _OnFailure_ y el que no se puede coger _Always_. 

	(io_k8s_api_apps_v1_StatefulSetSpec_template => io_k8s_api_apps_v1_StatefulSetSpec_template_spec_restartPolicy_Always & !io_k8s_api_apps_v1_StatefulSetSpec_template_spec_restartPolicy_Never & !io_k8s_api_apps_v1_StatefulSetSpec_template_spec_restartPolicy_OnFailure)
	(io_k8s_api_batch_v1_CronJob_spec_jobTemplate_spec_template => io_k8s_api_batch_v1_CronJob_spec_jobTemplate_spec_template_spec_restartPolicy_Never | io_k8s_api_batch_v1_CronJob_spec_jobTemplate_spec_template_spec_restartPolicy_OnFailure) & !io_k8s_api_batch_v1_CronJob_spec_jobTemplate_spec_template_spec_restartPolicy_Always

En total se generaron 19 restricciones.


### Agrupación de restricciones $... :

En desarrollo de más patrones y constraints...



### Archivo en Agrupaciones.md