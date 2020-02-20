import json
import boto3

def retrieve_required_tags_list(resource_type: str) -> list:
    """
    Loads the required tags configuration for each resource_type from central dynamodb table.
    :param resource_type:
    :return:
    """
    dynamodb_client = boto3.client('dynamodb')
    try : 
        get_required_tags_response = dynamodb_client.get_item(
            TableName              = "required-tags-table",
            Key                    = {"resource_type": {'S': resource_type}},
            ProjectionExpression   = "tags",
        )
        required_tags = [ key['S'] for key in get_required_tags_response['Item']['tags']['L'] ] 
    except :
        get_required_tags_response = dynamodb_client.get_item(
            TableName              = "required-tags-table",
            Key                    = {"resource_type": {'S': "Default"}},
            ProjectionExpression   = "tags",
        )
        required_tags = [ key['S'] for key in get_required_tags_response['Item']['tags']['L'] ] 

    return required_tags
    
# Iterate through required tags ensuring each required tag is present
def find_violation(current_tags, required_tags):
    violation = ""
    for rtag in required_tags:
        tag_present = False
        for tag in current_tags:
            if tag == rtag:
                tag_present = True
        if not tag_present:
            violation = violation + "\n" + rtag
    if violation == "":
        return None
    return  violation


def evaluate_compliance(configuration_item, required_tags):
    if configuration_item["configurationItemStatus"] == "ResourceDeleted":
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The configurationItem was deleted and therefore cannot be validated."
        }

    current_tags = configuration_item["tags"].keys()


    violation = find_violation(current_tags, required_tags)

    if violation:
        return {
            "compliance_type": "NON_COMPLIANT",
            "annotation": violation
        }

    return {
        "compliance_type": "COMPLIANT",
        "annotation": "This resource is compliant with the rule."
    }

def lambda_handler(event, context):
    invoking_event = json.loads(event["invokingEvent"])

    configuration_item = invoking_event["configurationItem"]

    required_tags = retrieve_required_tags_list(configuration_item["resourceType"])

    result_token = "No token found."
    if "resultToken" in event:
        result_token = event["resultToken"]

    evaluation = evaluate_compliance(configuration_item, required_tags)

    config = boto3.client("config")
    config.put_evaluations(
        Evaluations=[
            {
                "ComplianceResourceType":
                    configuration_item["resourceType"],
                "ComplianceResourceId":
                    configuration_item["resourceId"],
                "ComplianceType":
                    evaluation["compliance_type"],
                "Annotation":
                    evaluation["annotation"],
                "OrderingTimestamp":
                    configuration_item["configurationItemCaptureTime"]
            },
        ],
        ResultToken=result_token
    )