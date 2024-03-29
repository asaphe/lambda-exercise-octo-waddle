FROM public.ecr.aws/lambda/python:3.9

COPY main.py ${LAMBDA_TASK_ROOT}
COPY requirements.txt ${LAMBDA_TASK_ROOT}

RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

WORKDIR $LAMBDA_TASK_ROOT

CMD ["main.handler"]
