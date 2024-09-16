# Posibles agrupaciones de los features
En este archivo se expondrán las posibles agrupaciones que se forman de features que están relacionados con una funcionalidad general o concreta. Se utilizarán los nombres de los features para esta agrupación ya que en ellos se refleja el tipo y grupo que se pueden relacionar. Se podrá usar como elementos clave en cuanto a la agrupación, dispersión y posible automatización de los procesos.

Para tratar de realizar esta agrupación se diseñará un script que mediante palabras clave agrupe los features en conjuntos.

## Seguridad

Cada "miembro" de este grupo se basa en las siguientes palabras clave y tipos de recursos.


PodSecurityContext: holds pod-level security attributes and common container settings. Some fields are also present in container.securityContext.  Field values of container.securityContext take precedence over field values of PodSecurityContext
SecurityContext: holds security configuration that will be applied to a container. Some fields are present in both SecurityContext and PodSecurityContext.  When both are set, the values in SecurityContext take precedence
ClusterRole
ClusterRoleList
ClusterRoleBinding:
RoleBinding: 
_authorization__, authentication

## Configuración y variables de entorno

EnvVar
EnvVarSource
EnvFromSource


## Networking

NetworkPolicy/NetworkPolicyList/NetworkPolicySpec
_networking__
LoadBalancer
_Service__, ServiceList
_Ingress__, IngressList
EndpointsList

## Almacenamiento

## Escalabilidad y Disponibilidad