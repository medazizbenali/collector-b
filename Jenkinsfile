pipeline {
  agent any

  environment {
    APP_IMAGE = "collector-b:${env.BUILD_NUMBER}"
  }

  options {
    timestamps()
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Prepare CI env') {
      steps {
        sh '''
          set -eu

          # .env minimal pour CI (pas de secrets réels)
          cat > .env <<'EOF'
SECRET_KEY=ci-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000

DB_NAME=collector
DB_USER=collector
DB_PASSWORD=collectorpass
DB_HOST=db
DB_PORT=3306

REDIS_URL=redis://redis:6379/0
EOF

          # Override compose pour CI: pas de ports publics, pas de bind mount source
          cat > docker-compose.ci.yml <<'EOF'
services:
  web:
    volumes: []
    ports: []
  worker:
    volumes: []
EOF
        '''
      }
    }

    stage('Start services (MySQL/Redis)') {
      steps {
        sh '''
          set -eu
          COMPOSE="docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v \\"$WORKSPACE\\":\\"$WORKSPACE\\" -w \\"$WORKSPACE\\" docker/compose:latest"

          $COMPOSE -f docker-compose.yml -f docker-compose.ci.yml up -d db redis
          $COMPOSE ps
        '''
      }
    }

    stage('Unit + Integration tests') {
      steps {
        sh '''
          set -eu
          COMPOSE="docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v \\"$WORKSPACE\\":\\"$WORKSPACE\\" -w \\"$WORKSPACE\\" docker/compose:latest"

          # Build image depuis Dockerfile
          docker build -t ${APP_IMAGE} .

          # Migrations + tests dans le service web (réseau compose => db/redis accessibles)
          $COMPOSE -f docker-compose.yml -f docker-compose.ci.yml run --rm \
            -e DJANGO_SETTINGS_MODULE=config.settings \
            web sh -lc "
              python manage.py migrate --noinput &&
              python manage.py test -v 2
            "
        '''
      }
    }

    stage('Security (Bandit)') {
      steps {
        sh '''
          set -eu
          docker run --rm -v "$WORKSPACE:/src" -w /src python:3.12-slim sh -lc "
            pip install --no-cache-dir bandit &&
            bandit -r . -x */migrations/* -ll
          "
        '''
      }
    }

    stage('Vulnerabilities (Trivy fs)') {
      steps {
        sh '''
          set -eu
          docker run --rm -v "$WORKSPACE:/work" -w /work aquasec/trivy:latest fs \
            --scanners vuln,secret,config \
            --severity HIGH,CRITICAL \
            --exit-code 1 \
            .
        '''
      }
    }

    stage('Scan image (Trivy image)') {
      steps {
        sh '''
          set -eu
          docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image \
            --severity HIGH,CRITICAL \
            --exit-code 1 \
            ${APP_IMAGE}
        '''
      }
    }

    stage('Test image (Smoke)') {
      steps {
        sh '''
          set -eu
          COMPOSE="docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v \\"$WORKSPACE\\":\\"$WORKSPACE\\" -w \\"$WORKSPACE\\" docker/compose:latest"

          # Override compose pour démarrer web depuis l'image buildée
          cat > docker-compose.image.yml <<EOF
services:
  web:
    image: ${APP_IMAGE}
    command: >
      sh -c "
      python manage.py migrate --noinput &&
      python manage.py runserver 0.0.0.0:8000
      "
EOF

          $COMPOSE -f docker-compose.yml -f docker-compose.ci.yml -f docker-compose.image.yml up -d web
          $COMPOSE ps

          # Smoke test HTTP via Python (dans le conteneur web)
          $COMPOSE exec -T web python - <<'PY'
import urllib.request, sys, time

url = "http://localhost:8000/"

for attempt in range(1, 11):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            code = r.getcode()
            print("HTTP", code)
            if code < 400:
                sys.exit(0)
            sys.exit(1)
    except Exception as e:
        print(f"Attempt {attempt}/10 failed:", e)
        time.sleep(2)

print("Smoke test failed after retries")
sys.exit(1)
PY
        '''
      }
    }
  }

  post {
    always {
      sh '''
        set +e
        COMPOSE="docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v \\"$WORKSPACE\\":\\"$WORKSPACE\\" -w \\"$WORKSPACE\\" docker/compose:latest"

        $COMPOSE -f docker-compose.yml -f docker-compose.ci.yml down -v
        docker image rm -f ${APP_IMAGE} >/dev/null 2>&1 || true
      '''
    }
  }
}
