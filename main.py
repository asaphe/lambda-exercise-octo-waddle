import urllib.parse
from json import dumps as json_dumps
from os import environ

import boto3
from botocore.exceptions import ClientError

region = environ['AWS_REGION']

if len(region) == 0:
    region = 'eu-west-1'

s3 = boto3.client('s3')
ses = boto3.client('ses', region_name=region)


def send_email(s3_response, bucket, key):
    url = s3_response['url']
    uri = s3_response['uri']
    content_type = s3_response['content_type']

    SENDER = environ['SENDER']
    RECIPIENT = environ['RECIPIENT']
    CHARSET = "UTF-8"
    SUBJECT = f"Object {key} Uploaded to Bucket {bucket}"

    BODY_TEXT = (
                    f"Bucket: {bucket}\r\n"
                    f"Key: {key}\r\n"
                    f"URI: {uri}\r\n"
                    f"URL: {url}\r\n"
                    f"Object Type: {content_type}"
                    )

    try:
        response = ses.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])


def get_object(bucket, key):
    try:
        response_object = s3.get_object(Bucket=bucket, Key=key)
        location = s3.get_bucket_location(Bucket=bucket)['LocationConstraint']
        print(f"CONTENT TYPE: {response_object['ContentType']}")
        return {"content_type": response_object['ContentType'],
                "uri": f"s3://{bucket}/{key}",
                "url": f"https://{bucket}.s3.{location}.amazonaws.com/{key}"}
    except Exception as e:
        print(e)
        raise e


def handler(event, context):
    print("Received event: " + json_dumps(event, indent=2))
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'],
                                    encoding='utf-8')
    s3_response = get_object(bucket, key)
    send_email(s3_response, bucket, key)
