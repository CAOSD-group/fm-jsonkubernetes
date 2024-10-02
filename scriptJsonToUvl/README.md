## Relación entre los archivos de esta carpeta:

convert0Large.py genera 2 archivos: el feature model uvl en __kubernetes_combined_constraints.uvl__ y un conjunto de descripciones en __descriptions_01.json__. Este último es el que se usa en los análisis para agrupar las descripciones.


# AGRUPACIONES DE LAS CONSTRAINTS EN LOS ARCHIVOS

### Archivo en Agrupaciones.md

### Constraints de las referencias
La primera agrupación de constraints generadas automaticamente son las referencias o _$ref_ que tienen algunos esquemas. Es decir, de cada feature que se analiza y procesa en el script convert01Large.py se comprueba si en los detalles contienen referencias tipo "$ref" o inhibidas en propiedades como "items". Si hay referencias en los detalles de los esquemas, mediante la siguiente línea: *self.constraints.append(f"{full_name} => {ref_name}")* se añaden las constraints de las referencias a una lista que se muestra al final del modelo como _Constraints:_. Esto se decidió porque se puede observar de forma directa la relación que hay entre un feature y otro con las referencias hacia otros esquemas en el propio esquema. Algunas de las constraints obtenidas son las siguientes:

constraints
//Restricciones obtenidas de las referencias:

	io_k8s_api_admissionregistration_v1_MatchResources_excludeResourceRules => io_k8s_api_admissionregistration_v1_NamedRuleWithOperations
	io_k8s_api_admissionregistration_v1_MatchResources_namespaceSelector => io_k8s_apimachinery_pkg_apis_meta_v1_LabelSelector
	io_k8s_api_admissionregistration_v1_MatchResources_namespaceSelector_matchExpressions => io_k8s_apimachinery_pkg_apis_meta_v1_LabelSelectorRequirement
	io_k8s_api_admissionregistration_v1_MutatingWebhook_clientConfig => io_k8s_api_admissionregistration_v1_WebhookClientConfig
	io_k8s_api_admissionregistration_v1_MutatingWebhook_clientConfig_service => io_k8s_api_admissionregistration_v1_ServiceReference
    [...]

    io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIService_spec => io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIServiceSpec
	io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIService_spec_service => io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_ServiceReference
	io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIService_status => io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIServiceStatus
	io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIService_status_conditions => io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIServiceCondition
	io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIServiceList_items => io_k8s_kube_aggregator_pkg_apis_apiregistration_v1_APIService

Tras ver las constraints obtenidas desde el propio script que genera el modelo, se trato de obtener las demas inhibidas en las descripciones con un script externo y que procese los features filtrados en [descriptions_01.json](https://github.com/CAOSD-group/fm-json-kubernetes/blob/main/scriptJsonToUvl/descriptions_01.json). Este es un archivo que se obtiene al ejecutar el script principal y se filtran las descripciones de los features en 3 grupos diferentes:

- values: Agrupación de valores como extensiones del feature, valores concretos... se concentraban cualquier descripcion que contenga las palabras clave _(valid|values are|supported|acceptable|can be)_
- restrictions: cualquier descripcion que contenga las palabras clave _((allowed|conditions|should|must be|cannot be|if[\s\S]*?then|only|never|forbidden|disallowed))_
- dependencies: ** Sin examinar **

Después examinar las descripciones del fichero se definieron las siguientes reglas que generaron las siguientes constraints:

### Agrupación de restricciones por items:

En este caso se tratan de agrupar las reglas que tienen una funcionalidad similar de contener algun valor que coincida con '*'. Si algún elemento de los items contiene ese caracter, la propiedad existe y es de tamaño 1.
Ejemplo:
io_k8s_api_admissionregistration_v1_MatchResources_excludeResourceRules_apiGroups_items == '*' => io_k8s_api_admissionregistration_v1_MatchResources_excludeResourceRules_apiGroups

### Agrupación de restricciones valores que por defecto son mayor a cero:

En este caso se agrupan las constraints que por defecto o que su valor como número entero es mayor a cero. Se unieron varias comprobaciones para mostrar el mayor numero posible de estas descripciones, algunas de ellas son "positive", "non-negative" o "sequence number".
Ejemplo de algunas reglas:
	io_k8s_api_flowcontrol_v1_LimitResponse_queuing_handSize > 0
	io_k8s_api_flowcontrol_v1_LimitResponse_queuing_queueLengthLimit > 0
	io_k8s_api_flowcontrol_v1_LimitResponse_queuing_queues > 0
	io_k8s_api_policy_v1_Eviction_deleteOptions_gracePeriodSeconds > 0
	[...]


### Agrupación de restricciones que son String pero representan reglas que no sean vacios:

En esta agrupación se trata de adjuntar los features con descripciones que mencionan que un feature no tiene que ser vacío, y si es vacío se describen sucesos que no se pueden representar en el modelo con la sintaxis uvl.

Ejemplos: 
	!io_k8s_api_policy_v1_PodDisruptionBudget_status_disruptedPods
	!io_k8s_api_resource_v1alpha2_AllocationResult_resourceHandles
	!io_k8s_api_resource_v1alpha2_ResourceClaimParameters_driverRequests
	!io_k8s_api_storage_v1_CSIDriver_spec_volumeLifecycleModes
	[...]

### Agrupación de restricciones individuales o manuales* (Insertadas una a una con una definición específica)

Este grupo lo forman el resto de constraints que son insertadas por una definición individualizada, es decir, se define para una regla por una única descripción.
Ejemplos:
	io_k8s_api_admissionregistration_v1_MutatingWebhook_timeoutSeconds > 0 & io_k8s_api_admissionregistration_v1_MutatingWebhook_timeoutSeconds < 31

### Agrupación de restricciones valores que tienen limites maximos y minimos:

En desarrollo...