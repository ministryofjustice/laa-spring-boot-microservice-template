# Specify java runtime base image
FROM ghcr.io/ministryofjustice/laa-amazoncorretto:25-jre-alpine

USER root

# Set up working directory in the container
RUN mkdir -p /opt/laa-spring-boot-microservice/
WORKDIR /opt/laa-spring-boot-microservice/

# Copy the JAR file into the container
COPY spring-boot-microservice-service/build/libs/spring-boot-microservice-service-1.0.0.jar app.jar

# Set the default user
USER 1001

# Expose the server.port and management.server.port for the application
EXPOSE 8081 8181

# Run the JAR file
CMD java -jar app.jar