pipeline {
  agent any

  environment {
    APP_IMAGE = "collector-b:${env.BUILD_NUMBER}"
    SMOKE_NAME = "collectorb-smoke-${env.BUILD_NUMBER}"
  }

  options { timestamps() }

  stages {

    stage('Checkout') {
      steps { checkout scm }
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
    ports: []
    volumes: []
  worker:
    volumes: []
EOF

          docker compose version
        '''
      }
    }

    stage('Start DB & Redis') {
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
          docker build -t "${APP_IMAGE}" .
          docker image inspect "${APP_IMAGE}" >/dev/null
        '''
      }
    }

    stage('Unit + Integration tests') {
      steps {
        sh '''
          set -eu

          for i in $(seq 1 40); do
            if docker compose -f docker-compose.yml -f docker-compose.ci.yml exec -T db \
                mysqladmin ping -h 127.0.0.1 -uroot -prootpass --silent; then
              echo "MySQL is ready"
              break
            fi
            echo "Waiting MySQL... (${i}/40)"
            sleep 2
          done

          DB_CID="$(docker compose -f docker-compose.yml -f docker-compose.ci.yml ps -q db | head -n 1)"
          NET="$(docker inspect "$DB_CID" --format '{{range $k,$v := .NetworkSettings.Networks}}{{printf "%s\\n" $k}}{{end}}' | head -n 1)"
          echo "Using compose network: $NET"

          docker run --rm \
            --network "$NET" \
            --env-file .env \
            "${APP_IMAGE}" \
            sh -lc '
              set -eu
              cd /app
              python manage.py migrate --noinput
              python manage.py test -v 2
            '
        '''
      }
    }

    stage('Security (Bandit)') {
      steps {
        sh '''
          set -eu
          docker run --rm -v "$WORKSPACE:/src" -w /src python:3.12-slim sh -lc "
            pip install --no-cache-dir bandit >/dev/null &&
            bandit -r . -x */migrations/* -ll || true
          "
        '''
      }
    }

    stage('Vulnerabilities (Trivy image)') {
      steps {
        sh '''
          set -eu
          docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image \
            --severity HIGH,CRITICAL \
            --exit-code 0 \
            "${APP_IMAGE}" || true
        '''
      }
    }

    stage('Smoke test (container)') {
      steps {
        sh '''
          set -eu

          DB_CID="$(docker compose -f docker-compose.yml -f docker-compose.ci.yml ps -q db | head -n 1)"
          NET="$(docker inspect "$DB_CID" --format '{{range $k,$v := .NetworkSettings.Networks}}{{printf "%s\\n" $k}}{{end}}' | head -n 1)"
          echo "Using compose network: $NET"

          # Toujours nettoyer le conteneur smoke, même si le test échoue
          cleanup() {
            docker rm -f "${SMOKE_NAME}" >/dev/null 2>&1 || true
          }
          trap cleanup EXIT

          docker run -d --rm \
            --name "${SMOKE_NAME}" \
            --network "$NET" \
            --env-file .env \
            "${APP_IMAGE}" \
            sh -lc 'cd /app && python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000'

          # Smoke: on accepte que l'app réponde (même 400/403),
          # l'objectif est juste "le serveur est UP"
          docker run --rm --network "$NET" curlimages/curl:8.6.0 sh -lc '
            set -eu
            for i in $(seq 1 25); do
              code="$(curl -s -o /dev/null -w "%{http_code}" "http://'${SMOKE_NAME}':8000/" || true)"
              if [ "$code" != "000" ]; then
                echo "HTTP $code (server is up)"
                exit 0
              fi
              echo "Waiting app... (${i}/25)"
              sleep 2
            done
            echo "Smoke FAILED (no HTTP response)"
            exit 1
          '
        '''
      }
    }
  }

  post {
    always {
      sh '''
        set +e
        docker rm -f "${SMOKE_NAME}" >/dev/null 2>&1 || true
        docker compose -f docker-compose.yml -f docker-compose.ci.yml down -v || true
        rm -f docker-compose.ci.yml .env || true
        docker image rm -f "${APP_IMAGE}" >/dev/null 2>&1 || true
      '''
    }
  }
}
