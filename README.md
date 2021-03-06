# octo-waddle

> An exercise in creating an AWS Lambda.

This repository uses Github actions to build and deploy an AWS Lambda function.  
AWS S3 notifies the Lambda on any upload events, the Lambda sends an email for each event.

## Requirements

* AWS CLI Credentials
* Github Repository (CI/CD)

## CI/CD

Github actions is used to build the container image for every push. The image name is determined by `${{ github.ref_name }}`

> Note: During the build, Github secrets is used to set the sender and reciver email addresses. replacing the secrets in github will ensure the image contains the addresses.

```shell
SENDER_EMAIL: ${{ secrets.SENDER_EMAIL }}
RECIPIENT_EMAIL: ${{ secrets.RECIPIENT_EMAIL }}
```

> At runtime the email addresses can be changed by running:
>
> `aws lambda update-function-configuration --function-name 'octo-waddle' --environment "Variables={SENDER=${sender_email},RECIPIENT=${recipient_email}}"`

## Resources

* [Lambda S3 Example](https://docs.aws.amazon.com/lambda/latest/dg/with-s3-example.html)
* [Lambda functions defined as container images](https://docs.aws.amazon.com/lambda/latest/dg/configuration-images.html)
* [SES](https://aws.amazon.com/premiumsupport/knowledge-center/lambda-send-email-ses/)
* [Github Actions](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

## Steps

Follow the below steps to create the required resources.

### Shell

```shell
export AWS_REGION='eu-west-1'
export LAMBDA_NAME='octo-waddle'
```

Additionaly the following is required:

* aws_account_id
* image_name
* image_tag
* sender_email
* recipient_email

### AWS Resources

* Create an S3 Bucket

`aws s3api create-bucket --bucket "${LAMBDA_NAME}" --create-bucket-configuration '{LocationConstraint="eu-west-1"}'`

* Add a policy to our S3 bucket

`aws s3api put-bucket-policy --bucket "${LAMBDA_NAME}" --policy file://policies/octo-waddle-bucket-policy.json`

* Create an IAM role

```shell
aws iam create-role --role-name "${LAMBDA_NAME}" --assume-role-policy-document file://policies/octo-waddle-trust-relationship.json --tags '[{"Key": "Name", "Value": "octo-waddle"}]' --description 'octo-waddle role'
```

* Create IAM policies for our Role and attach them

```shell
sed -i "s/AWS_REGION/${AWS_REGION}/g" ./policies/*
sed -i "s/LAMBDA_NAME/${LAMBDA_NAME}/g" ./policies/*
sed -i "s/AWS_ACCOUNT_ID/${aws_account_id}/g" ./policies/*

for file in $(find ./policies -type file ! -iname "*trust*" ! -iname "*bucket*" -exec basename {} \;); do
  policy_name="$(echo ${file}| cut -d '.' -f1)"
  aws iam create-policy --policy-name "${policy_name}" --tags "[{\"Key\": \"Name\", \"Value\": \"${policy_name}\"}]" --policy-document "file://policies/${file}" --description "${policy_name}";
  aws iam attach-role-policy --policy-arn "arn:aws:iam::${aws_account_id}:policy/${policy_name}" --role-name "${LAMBDA_NAME}";
done
```

* Create ECR repository

`aws ecr create-repository --repository-name "${LAMBDA_NAME}" --image-scanning-configuration scanOnPush=true`

* Create the Lambda function

```shell
aws lambda create-function --function-name "${LAMBDA_NAME}" --package-type 'Image' --image-config '{"Command": ["main.handler"]}' --code "{\"ImageUri\": \"${aws_account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com/${image_name}:${image_tag}\"}" --environment "Variables={SENDER=${sender_email},RECIPIENT=${recipient_email}}" --role "arn:aws:iam::${aws_account_id}:role/octo-waddle" --description 'An Amazon S3 trigger that retrieves metadata for the object that has been updated.'
```

* Allow AWS S3 to invoke AWS Lambda

```shell
aws lambda add-permission --function-name "${LAMBDA_NAME}" --statement-id "s3_invoke_octo-waddle" --action "lambda:InvokeFunction" --principal s3.amazonaws.com --source-arn "arn:aws:s3:::octo-waddle" --source-account "${aws_account_id}"
```

* Add a notification configuration to the S3 bucket

`aws s3api put-bucket-notification-configuration --bucket "${LAMBDA_NAME}" --notification-configuration "file://policies/octo-waddle-bucket-notification.json"`

### AWS SES

* Create an SES email identity

`aws sesv2 create-email-identity --email-identity "${sender_email}" --tags "{\"Key\": \"Name\", \"Value\": \"${LAMBDA_NAME}-sender\"}"`

Complete the verification step by following the instructions in the email

### Build Docker Image

* Build and Tag container image

`docker build --tag "${aws_account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com/${image_name}:${image_tag}" .`

> Set `image_name` and `image_tag` environment variables

#### Push to ECR

* Login to ECR

`aws ecr get-login-password | docker login --username AWS --password-stdin "${aws_account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com"`

* Push the container image

`docker push "${aws_account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com/${image_name}:${image_tag}"`
