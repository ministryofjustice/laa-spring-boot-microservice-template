# laa-spring-boot-microservice-template

Template GitHub repository used for Spring Boot Java microservice projects.

The project uses the ```laa-ccms-spring-boot-gradle-plugin``` Gradle plugin which provides
sensible defaults for the following plugins:

- [Checkstyle](https://docs.gradle.org/current/userguide/checkstyle_plugin.html)
- [Dependency Management](https://plugins.gradle.org/plugin/io.spring.dependency-management)
- [Gradle Release](https://github.com/researchgate/gradle-release)
- [Jacoco](https://docs.gradle.org/current/userguide/jacoco_plugin.html)
- [Java](https://docs.gradle.org/current/userguide/java_plugin.html)
- [Maven Publish](https://docs.gradle.org/current/userguide/publishing_maven.html)
- [Spring Boot](https://plugins.gradle.org/plugin/org.springframework.boot)
- [Test Logger](https://github.com/radarsh/gradle-test-logger-plugin)
- [Versions](https://github.com/ben-manes/gradle-versions-plugin)

The plugin is provided by -  [laa-ccms-spring-boot-common](https://github.com/ministryofjustice/laa-ccms-spring-boot-common), where you can find
more information regarding setup and usage.

### Project structure
Includes the following subprojects:
- **spring-boot-microservice-api** - an example OpenAPI specification used for generating API stub interfaces and documentation.
- **spring-boot-microservice-service** - an example REST API with CRUD operations interfacing a JPA repository with an in-memory database.

### Build application
`./gradlew clean build`

### Run integration tests
`./gradlew integrationTest`

### Run application
`./gradlew :spring-boot-microservice-service:bootRun`

### Run application via Docker
`docker compose up`

### Swagger UI
http://localhost:8080/swagger-ui/index.html

### API docs JSON
http://localhost:8080/v3/api-docs

### Actuator endpoints
http://localhost:8080/actuator

http://localhost:8080/actuator/health

http://localhost:8080/actuator/info



