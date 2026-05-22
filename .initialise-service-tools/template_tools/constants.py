"""Template placeholder constants and shared configuration."""
from pathlib import Path

# Do NOT change the _T_* values — they are the exact strings present in the
# template source files and will be replaced during initialisation.
_T_ROOT_PROJECT               = "laa-spring-boot-microservice-template"
_T_KEBAB_FULL                 = "laa-spring-boot-microservice"
_T_KEBAB                      = "spring-boot-microservice"
_T_JAVA_PKG                   = "uk.gov.justice.laa.springboot.microservice"
_T_GRADLE_PKG                 = "uk.gov.laa.springboot.microservice"
_T_CLASS_PREFIX               = "SpringBootMicroservice"
_T_DISPLAY_NAME               = "LAA Spring Boot Microservice"
_T_SERVER_PORT                = "8081"
_T_MGMT_PORT                  = "8181"
_T_VERSION                    = "1.0.0"
_T_TESTCONTAINERS_BOM_VERSION = "1.20.6"

# .initialise-service-tools/ is at the repo root; .initialise-service-fragments is its sibling.
_TOOLS_DIR     = Path(__file__).parent.parent.resolve()
_FRAGMENTS_DIR = _TOOLS_DIR.parent / ".initialise-service-fragments"

SKIP_DIRS = {
    ".git", ".gradle", "build", "bin", "generated", ".idea", "__pycache__",
    ".initialise-service-fragments", ".initialise-service-tools",
}
SKIP_FILES = {
    "gradlew", "gradlew.bat", "gradle-wrapper.jar",
    "initialise-service.py",
}
SKIP_EXTS = {
    ".class", ".jar", ".exe", ".png", ".jpg", ".jpeg",
    ".svg", ".ico", ".bin", ".exec", ".gz", ".zip",
}
JAVA_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new",
    "package", "private", "protected", "public", "return", "short", "static",
    "strictfp", "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while",
}
