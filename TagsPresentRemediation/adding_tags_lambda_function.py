from typing import Dict, Tuple, AnyStr

import boto3
import json
import os
import logging

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'ERROR').upper()

logger = logging.getLogger()
level = logging.getLevelName(LOG_LEVEL)
logger.setLevel(level)

EC2_INSTANCE_CONFIG_TOPIC_ARN = os.getenv("EC2_INSTANCE_CONFIG_TOPIC_ARN", "ec2_instance_topic")
S3_BUCKET_CONFIG_TOPIC_ARN = os.getenv("S3_BUCKET_CONFIG_TOPIC_ARN", "s3_bucket_topic")
RDS_INSTANCE_CONFIG_TOPIC_ARN = os.getenv("RDS_INSTANCE_CONFIG_TOPIC_ARN", "rds_instance_topic")

TOPIC_ARNS_TO_RESOURCE_TYPES = {
    EC2_INSTANCE_CONFIG_TOPIC_ARN: "AWS::EC2::Instance",
    S3_BUCKET_CONFIG_TOPIC_ARN: "AWS::S3::Bucket",
    RDS_INSTANCE_CONFIG_TOPIC_ARN: "AWS::RDS::DBInstance"
}


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


def build_new_tags(resource_type: str, existing_tags: dict) -> dict:
    """
    Builds the new tags given the resource_type and existing_tags
    :param resource_type:
    :param existing_tags:
    :return:
    """
    required_tags_list = retrieve_required_tags_list(resource_type)

    new_tags = {}

    # Runs through list of required tags
    for t in required_tags_list:

        # Checks if the tag is present in the current tags, if present then skip this block, or else add the tag
        if t not in existing_tags.keys():
            new_tags[t] = ""

    return new_tags


def fetch_configuration_item_data(resource_id: str, resource_type: str) -> Tuple[AnyStr, Dict]:
    """
    Fetches the configuration item's configuration history record from the AWS Config service. This gives us the
    resource arn as well as the existing tags.
    :param resource_id:
    :param resource_type:
    :return:
    """
    config_client = boto3.client('config')
    get_resource_config_history_response = config_client.get_resource_config_history(
        resourceType=resource_type,
        resourceId=resource_id,
        limit=1
    )
    configuration_item = get_resource_config_history_response.get('configurationItems')[0]
    return configuration_item.get('arn'), configuration_item.get('tags', {})


def lambda_handler(event, context):
    logger.debug('## EVENT')
    logger.debug(event)
    logger.debug('## EVENT CONTEXT')
    logger.debug(context)

    for record in event['Records']:
        try:
            logger.debug('## EVENT RECORD')
            logger.debug(record)

            body = json.loads(record.get('body'))

            resource_id = body.get('Message')

            resource_type = TOPIC_ARNS_TO_RESOURCE_TYPES[body.get('TopicArn')]

            logger.info('## TAGGING RESOURCE: resource_type: {resource_type}, resource_id: {resource_id}'.format(
                resource_type=resource_type,
                resource_id=resource_id
            ))

            resource_arn, existing_tags = fetch_configuration_item_data(resource_id, resource_type)

            logger.info('## Existing tags on resource:\n{}'.format(existing_tags))

            new_tags = build_new_tags(resource_type, existing_tags)

            logger.info('## New tags to be added to resource:\n{}'.format(new_tags))

            if len(new_tags) > 0:
                tagging_api_client = boto3.client('resourcegroupstaggingapi')
                response = tagging_api_client.tag_resources(ResourceARNList=[resource_arn], Tags=new_tags)
                logger.info(response)

        except Exception as e:
            logger.error(e)
            raise e
