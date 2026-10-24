FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml ./
COPY labkg ./labkg
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home labkg && mkdir /data && chown labkg /data
USER 10001:10001
ENV LABKG_DB=/data/labkg.sqlite
EXPOSE 8765
CMD ["labkg", "serve", "--host", "0.0.0.0"]
