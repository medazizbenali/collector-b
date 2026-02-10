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

          # IMPORTANT: workspace dans Jenkins conteneur != chemin sur la VM
          WS_BASE="$(basename "$WORKSPACE")"
          HOST_WS="/var/lib/docker/volumes/jenkins_home/_data/workspace/${WS_BASE}"

          echo "Container WORKSPACE: $WORKSPACE"
          echo "Host workspace:      $HOST_WS"
          ls -la "$HOST_WS" | sed -n '1,120p'

          if [ -f "$HOST_WS/docker-compose.yml" ]; then
            BASE_COMPOSE="docker-compose.yml"
          elif [ -f "$HOST_WS/docker-compose.yaml" ]; then
            BASE_COMPOSE="docker-compose.yaml"
          else
            echo "No docker-compose file found in HOST_WS"
            exit 1
          fi

          compose() {
            docker run --rm \
              -v /var/run/docker.sock:/var/run/docker.sock \
              -v "$HOST_WS:/work" \
              -w /work \
              docker/compose:latest "$@"
          }

          compose version
          compose -f "$BASE_COMPOSE" -f docker-compose.ci.yml up -d db redis
          compose ps
        '''
      }
    }

    stage('Unit + Integration tests') {
      steps {
        sh '''
          set -eu

          WS_BASE="$(basename "$WORKSPACE")"
          HOST_WS="/var/lib/docker/volumes/jenkins_home/_data/workspace/${WS_BASE}"

          if [ -f "$HOST_WS/docker-compose.yml" ]; then
            BASE_COMPOSE="docker-compose.yml"
          elif [ -f "$HOST_WS/docker-compose.yaml" ]; then
            BASE_COMPOSE="docker-compose.yaml"
          else
            echo "No docker-compose file found in HOST_WS"
            exit 1
          fi

          compose() {
            docker run --rm \
              -v /var/run/docker.sock:/var/run/docker.sock \
              -v "$HOST_WS:/work" \
              -w /work \
              docker/compose:latest "$@"
          }

          docker build -t ${APP_IMAGE} .

          # Petite attente (si MySQL pas prêt on ajoutera un wait-for-db)
          sleep 3

          compose -f "$BASE_COMPOSE" -f docker-compose.ci.yml run --rm \
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
          WS_BASE="$(basename "$WORKSPACE")"
          HOST_WS="/var/lib/docker/volumes/jenkins_home/_data/workspace/${WS_BASE}"

          docker run --rm -v "$HOST_WS:/src" -w /src python:3.12-slim sh -lc "
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
          WS_BASE="$(basename "$WORKSPACE")"
          HOST_WS="/var/lib/docker/volumes/jenkins_home/_data/workspace/${WS_BASE}"

          docker run --rm -v "$HOST_WS:/work" -w /work aquasec/trivy:latest fs \
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

          WS_BASE="$(basename "$WORKSPACE")"
          HOST_WS="/var/lib/docker/volumes/jenkins_home/_data/workspace/${WS_BASE}"

          if [ -f "$HOST_WS/docker-compose.yml" ]; then
            BASE_COMPOSE="docker-compose.yml"
          elif [ -f "$HOST_WS/docker-compose.yaml" ]; then
            BASE_COMPOSE="docker-compose.yaml"
          else
            echo "No docker-compose file found in HOST_WS"
            exit 1
          fi

          compose() {
            docker run --rm \
              -v /var/run/docker.sock:/var/run/docker.sock \
              -v "$HOST_WS:/work" \
              -w /work \
              docker/compose:latest "$@"
          }

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

          compose -f "$BASE_COMPOSE" -f docker-compose.ci.yml -f docker-compose.image.yml up -d web
          compose ps

          compose exec -T web python - <<'PY'
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

        WS_BASE="$(basename "$WORKSPACE")"
        HOST_WS="/var/lib/docker/volumes/jenkins_home/_data/workspace/${WS_BASE}"

        if [ -f "$HOST_WS/docker-compose.yml" ]; then
          BASE_COMPOSE="docker-compose.yml"
        elif [ -f "$HOST_WS/docker-compose.yaml" ]; then
          BASE_COMPOSE="docker-compose.yaml"
        else
          BASE_COMPOSE="docker-compose.yml"
        fi

        compose() {
          docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v "$HOST_WS:/work" \
            -w /work \
            docker/compose:latest "$@"
        }

        compose -f "$BASE_COMPOSE" -f docker-compose.ci.yml down -v
        docker image rm -f ${APP_IMAGE} >/dev/null 2>&1 || true
      '''
    }
  }
}
