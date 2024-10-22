import json
from collections import defaultdict

# Palabras clave por grupo
keywords = {
    #"Seguridad": ["policy", "role", "binding", "security", "account", "certificate", "secret"],
    "Security": ["PodSecurityContext", "SecurityContext", "ClusterRole", "ClusterRoleList", "ClusterRoleBinding", "RoleBinding",
    "ServiceAccount", "authentication", "_authorization_", "IngressTLS", "NetworkPolicy", "role", "binding", "security", "account", "certificate", "secret"],
    "EnvVars": ["EnvVar", "EnvVarSource", "EnvFromSource"], 
    "Networking": ["NetworkPolicy", "NetworkPolicyList", "NetworkPolicySpec", "_networking_", "LoadBalancer", "_Service_" , "ServiceList", "_Ingress_", "IngressList", "EndpointsList"]
}

# Función para asignar un grupo a un feature basado en el nombre
def assign_group(feature_name):
    for group, words in keywords.items():
        if any(word in feature_name.lower() for word in words):
            return group
    return "Sin grupo"