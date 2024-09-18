¡Nuevo! Combinaciones de teclas … Las combinaciones de teclas de Drive se han actualizado para que puedas navegar escribiendo las primeras letras
Resultados tras el análsisi con la herramienta https://fmfactlabel.adabyron.uma.es/


### False-optionals features:

io_k8s_apimachinery_pkg_apis_meta_v1_Time,
io_k8s_apimachinery_pkg_apis_meta_v1_FieldsV1,
io_k8s_apimachinery_pkg_runtime_RawExtension,
io_k8s_apimachinery_pkg_api_resource_Quantity,
io_k8s_apimachinery_pkg_apis_meta_v1_MicroTime,
io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_JSONSchemaPropsOrBool,
io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_JSON,
io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_JSONSchemaPropsOrArray,
io_k8s_apiextensions_apiserver_pkg_apis_apiextensions_v1_CustomResourceSubresourceStatus

Para solucionar los Fail Optionals se necesita agregar la mandotoriedad a la hora de crear las referencias,
es decir, si hay una constraint de una referencia directa que relaciona un feature al otro, este tiene que ser
mandatory, sino entra en conflicto con que esta en optional al no tener una representación firme en los esquemas
Solucionado: Ajuste de script para las refs simples en 2 puntos:


### Dead Features:
io_k8s_api_certificates_v1_CertificateSigningRequest_spec_usages_ipsec,sgc,auth,only,sign,signing,
io_k8s_api_certificates_v1_CertificateSigningRequestSpec_usages_ipsec

Posibles errores en el alterative => genero los features de items simples cuando quizas puedan generar problemas con las alternativas ya que algunas son optionals y aparte se usa el x-or ...
Aunque al quitar los features de items simples sigue manteniendose el error.
items simples añadidos por las constraints, para la "Agrupación de restricciones por item", en algunos puntos son necesarios pero quizas no siempre sea necesario generar ese feature.

Solucionado: Quitando comillas etc
### Probar ajuste generando solo los items necesarios que salgan en las reglas