FROM python:3.8

WORKDIR /app

COPY "requirements/base.txt" ./
RUN pip install --no-cache-dir -r "base.txt"

COPY dist/* ./
COPY test_build_install_run.sh .

CMD [ "/app/test_build_install_run.sh" ]
