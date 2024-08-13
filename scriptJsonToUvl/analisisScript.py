import re
import json

# Función para cargar las características desde el archivo JSON
def load_json_features(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# Descripciones categorizadas como restricciones (usaremos algunas para probar)
restrictions = [
    ("io_k8s_api_admissionregistration_v1_MatchResources_excludeResourceRules_apiGroups",
     "APIGroups is the API groups the resources belong to. '*' is all groups. If '*' is present, the length of the slice must be one. Required."),
    ("io_k8s_api_admissionregistration_v1_MatchResources_excludeResourceRules_apiVersions",
     "APIVersions is the API versions the resources belong to. '*' is all versions. If '*' is present, the length of the slice must be one. Required."),
    ("io_k8s_api_admissionregistration_v1_MatchResources_excludeResourceRules_operations",
     "Operations is the operations the admission hook cares about - CREATE, UPDATE, DELETE, CONNECT or * for all of those operations and any future admission operations that are added. If '*' is present, the length of the slice must be one. Required."),
    ("io_k8s_api_admissionregistration_v1_MatchResources_excludeResourceRules_resourceNames",
     "ResourceNames is an optional white list of names that the rule applies to. An empty set means that everything is allowed."),
    ("io_k8s_api_admissionregistration_v1_MatchResources_namespaceSelector",
     "NamespaceSelector decides whether to run the admission control policy on an object based on whether the namespace for that object matches the selector. If the object itself is a namespace, the matching is performed on object.metadata.labels. If the object is another cluster scoped resource, it never skips the policy."),
    ("io_k8s_api_admissionregistration_v1_MatchResources_namespaceSelector_matchExpressions_values",
     "values is an array of string values. If the operator is In or NotIn, the values array must be non-empty. If the operator is Exists or DoesNotExist, the values array must be empty. This array is replaced during a strategic merge patch."),
    ("io_k8s_api_admissionregistration_v1_MatchResources_namespaceSelector_matchLabels",
     "matchLabels is a map of {key,value} pairs. A single {key,value} in the matchLabels map is equivalent to an element of matchExpressions, whose key field is \"key\", the operator is \"In\", and the values array contains only \"value\". The requirements are ANDed."),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhook_clientConfig_service",
     "`service` is a reference to the service for this webhook. Either `service` or `url` must be specified.\n\nIf the webhook is running within the cluster, then you should use `service`."),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhook_clientConfig_url",
     "`url` gives the location of the webhook, in standard URL form (`scheme://host:port/path`). Exactly one of `url` or `service` must be specified.\n\nThe `host` should not refer to a service running in the cluster; use the `service` field instead. The host might be resolved via external DNS in some apiservers (e.g., `kube-apiserver` cannot resolve in-cluster DNS as that would be a layering violation). `host` may also be an IP address.\n\nPlease note that using `localhost` or `127.0.0.1` as a `host` is risky unless you take great care to run this webhook on all hosts which run an apiserver which might need to make calls to this webhook. Such installs are likely to be non-portable, i.e., not easy to turn up in a new cluster.\n\nThe scheme must be \"https\"; the URL must begin with \"https://\".\n\nA path is optional, and if present may be any string permissible in a URL. You may use the path to pass an arbitrary string to the webhook, for example, a cluster identifier.\n\nAttempting to use a user or basic auth e.g. \"user:password@\" is not allowed. Fragments (\"#...\") and query parameters (\"?...\") are not allowed, either."),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhook_matchConditions",
     "MatchConditions is a list of conditions that must be met for a request to be sent to this webhook. Match conditions filter requests that have already been matched by the rules, namespaceSelector, and objectSelector. An empty list of matchConditions matches all requests. There are a maximum of 64 match conditions allowed.\n\nThe exact matching logic is (in order):\n  1. If ANY matchCondition evaluates to FALSE, the webhook is skipped.\n  2. If ALL matchConditions evaluate to TRUE, the webhook is called.\n  3. If any matchCondition evaluates to an error (but none are FALSE):\n     - If failurePolicy=Fail, reject the request\n     - If failurePolicy=Ignore, the error is ignored and the webhook is skipped"),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhook_name",
     "The name of the admission webhook. Name should be fully qualified, e.g., imagepolicy.kubernetes.io, where \"imagepolicy\" is the name of the webhook, and kubernetes.io is the name of the organization. Required."),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhook_namespaceSelector",
     "NamespaceSelector decides whether to run the webhook on an object based on whether the namespace for that object matches the selector. If the object itself is a namespace, the matching is performed on object.metadata.labels. If the object is another cluster scoped resource, it never skips the webhook.\n\nFor example, to run the webhook on any objects whose namespace is not associated with \"runlevel\" of \"0\" or \"1\";  you will set the selector as follows: \"namespaceSelector\": {\n  \"matchExpressions\": [\n    {\n      \"key\": \"runlevel\",\n      \"operator\": \"NotIn\",\n      \"values\": [\n        \"0\",\n        \"1\"\n      ]\n    }\n  ]\n}\n\nIf instead you want to only run the webhook on any objects whose namespace is associated with the \"environment\" of \"prod\" or \"staging\"; you will set the selector as follows: \"namespaceSelector\": {\n  \"matchExpressions\": [\n    {\n      \"key\": \"environment\",\n      \"operator\": \"In\",\n      \"values\": [\n        \"prod\",\n        \"staging\"\n      ]\n    }\n  ]\n}\n\nSee https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/ for more examples of label selectors.\n\nDefault to the empty LabelSelector, which matches everything."),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhook_objectSelector",
     "ObjectSelector decides whether to run the webhook based on if the object has matching labels. objectSelector is evaluated against both the oldObject and newObject that would be sent to the webhook, and is considered to match if either object matches the selector. A null object (oldObject in the case of create, or newObject in the case of delete) or an object that cannot have labels (like a DeploymentRollback or a PodProxyOptions object) is not considered to match. Use the object selector only if the webhook is opt-in, because end users may skip the admission webhook by setting the labels. Default to the empty LabelSelector, which matches everything."),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhook_timeoutSeconds",
     "TimeoutSeconds specifies the timeout for this webhook. After the timeout passes, the webhook call will be ignored or the API call will fail based on the failure policy. The timeout value must be between 1 and 30 seconds. Default to 10 seconds."),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhookConfiguration_apiVersion",
     "APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources"),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhookConfiguration_kind",
     "Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds"),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhookConfiguration_metadata_annotations",
     "Annotations is an unstructured key value map stored with a resource that may be set by external tools to store and retrieve arbitrary metadata. They are not queryable and should be preserved when modifying objects. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/annotations"),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhookConfiguration_metadata_creationTimestamp",
     "CreationTimestamp is a timestamp representing the server time when this object was created. It is not guaranteed to be set in happens-before order across separate operations. Clients may not set this value. It is represented in RFC3339 form and is in UTC.\n\nPopulated by the system. Read-only. Null for lists. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata"),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhookConfiguration_metadata_deletionGracePeriodSeconds",
     "Number of seconds allowed for this object to gracefully terminate before it will be removed from the system. Only set when deletionTimestamp is also set. May only be shortened. Read-only."),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhookConfiguration_metadata_deletionTimestamp",
     "DeletionTimestamp is RFC 3339 date and time at which this resource will be deleted. This field is set by the server when a graceful deletion is requested by the user, and is not directly settable by a client. The resource is expected to be deleted (no longer visible from resource lists, and not reachable by name) after the time in this field, once the finalizers list is empty. As long as the finalizers list contains items, deletion is blocked. Once the deletionTimestamp is set, this value may not be unset or be set further into the future, although it may be shortened or the resource may be deleted prior to this time. For example, a user may request that a pod is deleted in 30 seconds. The Kubelet will react by sending a graceful termination signal to the containers in the pod. After that 30 seconds, the Kubelet will send a hard termination signal (SIGKILL) to the container and after cleanup, remove the pod from the API. In the presence of network partitions, this object may still exist after this timestamp, until an administrator or automated process can determine the resource is fully terminated. If not set, graceful deletion of the object has not been requested.\n\nPopulated by the system when a graceful deletion is requested. Read-only. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#metadata"),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhookConfiguration_metadata_finalizers",
     "Must be empty before the object is deleted from the registry. Each entry is an identifier for the responsible component that will remove the entry from the list. If the deletionTimestamp of the object is non-nil, entries in this list can only be removed. Finalizers may be processed and removed in any order.  Order is NOT enforced because it introduces significant risk of stuck finalizers. finalizers is a shared field, any actor with permission can reorder it. If the finalizer list is processed in order, then this can lead to a situation in which the component responsible for the first finalizer in the list is waiting for a signal (field value, external system, or other) produced by a component responsible for a finalizer later in the list, resulting in a deadlock. Without enforced ordering finalizers are free to order amongst themselves and are not vulnerable to ordering changes in the list."),
    ("io_k8s_api_admissionregistration_v1_MutatingWebhookConfiguration_metadata_generation",
     "A sequence number representing a specific generation of the desired state. Populated by the system. Read-only."),
]

# Función para convertir descripciones en UVL
def convert_to_uvl(feature_key, description):
    uvl_rule = ""
    
    # Patrones para reconocer diferentes restricciones
    if "If '*' is present" in description and "length of the slice must be one" in description:
        uvl_rule = f"{feature_key} == '*' => length({feature_key}) == 1"
    elif "length of the slice must be one" in description:
        uvl_rule = f"{feature_key} == '*' => length({feature_key}) == 1"
    elif "values array must be non-empty" in description:
        uvl_rule = f"{feature_key} => notEmpty({feature_key})"
    elif "values array must be empty" in description:
        uvl_rule = f"{feature_key} => isEmpty({feature_key})"
    elif "an optional white list of names" in description:
        uvl_rule = f"{feature_key} == '' || {feature_key} == '*'"
    ##Adicion mas reglas
    elif "values array must be non-empty" in description:
        uvl_rule = f"length({feature_key}) > 0"
    elif "values array must be empty" in description:
        uvl_rule = f"length({feature_key}) == 0"
    elif "matchLabels is a map of {key,value} pairs" in description:
        uvl_rule = f"exists({feature_key}) => type({feature_key}) == 'map'"
    elif "reference to the service" in description:
        uvl_rule = f"exists({feature_key}.service) or exists({feature_key}.url)"
    elif "location of the webhook" in description:
        uvl_rule = f"exists({feature_key}.url) => startsWith({feature_key}.url, 'https://')"
    elif "MatchConditions is a list" in description:
        uvl_rule = f"length({feature_key}) <= 64"
    elif "name should be fully qualified" in description:
        uvl_rule = f"exists({feature_key}) => isFullyQualified({feature_key})"
    elif "NamespaceSelector decides" in description:
        uvl_rule = f"exists({feature_key}) => type({feature_key}) == 'LabelSelector'"
    elif "ObjectSelector decides" in description:
        uvl_rule = f"exists({feature_key}) => type({feature_key}) == 'LabelSelector'"
    elif "TimeoutSeconds specifies" in description:
        uvl_rule = f"1 <= {feature_key} <= 30"
    elif "APIVersion defines" in description:
        uvl_rule = f"exists({feature_key}) => isAPIVersion({feature_key})"
    elif "Kind is a string value" in description:
        uvl_rule = f"exists({feature_key}) => isKind({feature_key})"
    elif "Annotations is an unstructured key value map" in description:
        uvl_rule = f"exists({feature_key}) => type({feature_key}) == 'map'"
    elif "CreationTimestamp is a timestamp" in description:
        uvl_rule = f"exists({feature_key}) => isTimestamp({feature_key})"
    elif "Number of seconds allowed" in description:
        uvl_rule = f"exists({feature_key}) => {feature_key} >= 0"
    elif "DeletionTimestamp is RFC 3339 date and time" in description:
        uvl_rule = f"exists({feature_key}) => isRFC3339({feature_key})"
    elif "Must be empty before the object is deleted" in description:
        uvl_rule = f"exists({feature_key}) => length({feature_key}) == 0"
    elif "A sequence number representing" in description:
        uvl_rule = f"exists({feature_key}) => isSequenceNumber({feature_key})"
    else:
        uvl_rule = f"# No matching rule for: {feature_key} - {description}"

    return uvl_rule

# Aplicar la conversión a las descripciones de prueba
uvl_rules = [convert_to_uvl(feature_key, desc) for feature_key, desc in restrictions]

# Imprimir las reglas UVL generadas
for uvl_rule in uvl_rules:
    print(uvl_rule)





"""import json
import re

# Cargar las características desde el archivo JSON
def load_json_features(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# Extraer bloques de texto relevantes en función de patrones específicos
def extract_important_info(features):
    important_info = {
        'values': [],
        'restrictions': [],
        'dependencies': []
    }


    # Patrones para buscar en las descripciones (añadiendo palabras clave adicionales)
    patterns = {
        'values': re.compile(r'(valid|values are|supported|acceptable|can be)[\s\S]*?(?=\n[A-Z]|\Z)', re.IGNORECASE),
        'restrictions': re.compile(r'(allowed|conditions|should|must be|cannot be|if[\s\S]*?then|only|never|forbidden|disallowed)[\s\S]*?(?=\n[A-Z]|\Z)', re.IGNORECASE),
        'dependencies': re.compile(r'(depends on|requires|if[\s\S]*?only if|relies on|contingent upon|related to)[\s\S]*?(?=\n[A-Z]|\Z)', re.IGNORECASE)
    }
    ###
    # Patrones para capturar frases completas
    patterns = {
        'values': re.compile(r'(?:(?:must|should|can|are allowed to|values include|values are|supported|acceptable|can be|may be)[\s\S]*?)(?=\.\s|\.$)', re.IGNORECASE),
        'restrictions': re.compile(r'(?:(?:must not|cannot|should not|cannot be|only|never|forbidden|disallowed|prohibited|=>|>|<|==|!=)[\s\S]*?)(?=\.\s|\.$)', re.IGNORECASE),
        'dependencies': re.compile(r'(?:(?:depends on|requires|if[\s\S]*?only if|relies on|contingent upon|related to|associated with)[\s\S]*?)(?=\.\s|\.$)', re.IGNORECASE)
    }
    ###

    for feature_name, description in features.items():
        for category, pattern in patterns.items():
            matches = pattern.findall(description)
            if matches:
                important_info[category].extend(matches)

    return important_info

# Guardar la información importante en archivos JSON y TXT
def save_important_info(info, json_file_path, txt_file_path):
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=4, ensure_ascii=False)
    
    with open(txt_file_path, 'w', encoding='utf-8') as f:
        for category, texts in info.items():
            f.write(f"{category.upper()}:\n")
            for text in texts:
                f.write(f"  {text.strip()}\n")
            f.write("\n")

# Rutas de archivo
json_file_path = 'C:/projects/investigacion/scriptJsonToUvl/descriptions_02.json'
important_info_json_path = 'C:/projects/investigacion/scriptJsonToUvl/important_info.json'
important_info_txt_path = 'C:/projects/investigacion/scriptJsonToUvl/important_info.txt'

# Cargar datos
features = load_json_features(json_file_path)

# Extraer información importante
important_info = extract_important_info(features)

# Guardar la información importante
save_important_info(important_info, important_info_json_path, important_info_txt_path)

print("Información importante extraída y guardada en 'important_info.json' y 'important_info.txt'")
"""

