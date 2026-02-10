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

          # Override CI: pas de ports publics, pas de bind mounts
          cat > docker-compose.ci.yml <<'EOF'
services:
  web:
    volumes: []
    ports: []
  worker:
    volumes: []
EOF

          docker compose version
        '''
      }
    }

    stage('Start services (MySQL/Redis)') {
      steps {
        sh '''
          set -eu
          docker compose -f docker-compose.yml -f docker-compose.ci.yml up -d db redis
          docker compose ps
        '''
      }
    }

    stage('Build image') {
      steps {
        sh '''
          set -eu
          docker build -t ${APP_IMAGE} .
        '''
      }
    }

    stage('Unit + Integration tests') {
      steps {
        sh '''
          set -eu

          # Attendre MySQL
          for i in $(seq 1 30); do
            if docker compose -f docker-compose.yml -f docker-compose.ci.yml exec -T db \
              mysqladmin ping -h 127.0.0.1 -uroot --silent 2>/dev/null; then
              echo "MySQL is ready"
              break
            fi
            echo "Waiting MySQL... ($i/30)"
            sleep 2
          done

          # IMPORTANT: empêcher docker compose de rebuild (sinon buildx requis)
          cat > docker-compose.test.yml <<EOF
services:
  web:
    image: ${APP_IMAGE}
    build: null
EOF

      docker compose -f docker-compose.yml -f docker-compose.ci.yml -f docker-compose.test.yml run --rm \
  -e DJANGO_SETTINGS_MODULE=config.settings \
  web sh -lc '
    set -eu
    MP="$(find / -maxdepth 4 -name manage.py 2>/dev/null | head -n 1 || true)"
    if [ -z "$MP" ]; then
      echo "manage.py not found in container. Listing common dirs:"
      ls -la / /app /code /src /usr/src 2>/dev/null || true
      exit 2
    fi
    echo "Found manage.py at: $MP"
    cd "$(dirname "$MP")"
    python manage.py migrate --noinput
    python manage.py test -v 2
  '

    stage('Security (Bandit)') {
      steps {
        sh '''
          set -eu
          docker run --rm -v "$PWD:/src" -w /src python:3.12-slim sh -lc "
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
          docker run --rm -v "$PWD:/work" -w /work aquasec/trivy:latest fs \
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

    stage('Smoke test (container)') {
      steps {
        sh '''
          set -eu

          # Force web à utiliser l'image buildée
          cat > docker-compose.image.yml <<EOF
services:
  web:
    image: ${APP_IMAGE}
    build: null
    command: >
      sh -c "
      python manage.py migrate --noinput &&
      python manage.py runserver 0.0.0.0:8000
      "
EOF

          docker compose -f docker-compose.yml -f docker-compose.ci.yml -f docker-compose.image.yml up -d web
          docker compose ps

          # Smoke test HTTP depuis le conteneur web (localhost = conteneur web)
          docker compose -f docker-compose.yml -f docker-compose.ci.yml -f docker-compose.image.yml exec -T web python - <<'PY'
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
        docker compose -f docker-compose.yml -f docker-compose.ci.yml down -v
        rm -f docker-compose.image.yml docker-compose.test.yml docker-compose.ci.yml .env || true
        docker image rm -f ${APP_IMAGE} >/dev/null 2>&1 || true
      '''
    }
  }
}
