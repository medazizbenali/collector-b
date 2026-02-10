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

          # .env CI (pas de vrais secrets)
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

          # CI override : on évite d’exposer des ports + on neutralise les bind mounts
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

          # Attendre MySQL
          for i in $(seq 1 40); do
            if docker compose -f docker-compose.yml -f docker-compose.ci.yml exec -T db \
                mysqladmin ping -h 127.0.0.1 -uroot -prootpass --silent; then
              echo "MySQL is ready"
              break
            fi
            echo "Waiting MySQL... (${i}/40)"
            sleep 2
          done

          # Récupérer le network du projet compose (pour que "db" et "redis" soient résolus)
          DB_CID="$(docker compose -f docker-compose.yml -f docker-compose.ci.yml ps -q db | head -n 1)"
          if [ -z "$DB_CID" ]; then
            echo "ERROR: DB container not found"
            docker compose -f docker-compose.yml -f docker-compose.ci.yml ps || true
            exit 2
          fi

          NET="$(docker inspect "$DB_CID" --format '{{range $k,$v := .NetworkSettings.Networks}}{{printf "%s\\n" $k}}{{end}}' | head -n 1)"
          if [ -z "$NET" ]; then
            echo "ERROR: Compose network not found"
            docker inspect "$DB_CID" || true
            exit 2
          fi
          echo "Using compose network: $NET"

          # IMPORTANT: on n'utilise PAS `docker compose run web` (bind mounts cassés en Jenkins-in-Docker)
          docker run --rm \
            --network "$NET" \
            --env-file .env \
            "${APP_IMAGE}" \
            sh -lc '
              set -eu
              cd /app
              ls -la | head -n 50
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
          # non bloquant au début (tu pourras passer à exit 1 plus tard)
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
          # non bloquant au début (tu pourras forcer HIGH/CRITICAL plus tard)
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

          # Lancer l’app (sans ports, on teste en interne via curl)
          CID="$(docker run -d --rm \
            --name "collectorb-smoke-${BUILD_NUMBER}" \
            --network "$NET" \
            --env-file .env \
            "${APP_IMAGE}" \
            sh -lc 'cd /app && python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000'
          )"

          # Attendre que ça réponde (depuis un conteneur dans le même network)
          docker run --rm --network "$NET" curlimages/curl:8.6.0 sh -lc '
            set -eu
            for i in $(seq 1 20); do
              if curl -fsS http://collectorb-smoke-'${BUILD_NUMBER}':8000/ >/dev/null; then
                echo "Smoke OK"
                exit 0
              fi
              echo "Waiting app... (${i}/20)"
              sleep 2
            done
            echo "Smoke FAILED"
            exit 1
          '

          docker stop "$CID" >/dev/null 2>&1 || true
        '''
      }
    }
  }

  post {
    always {
      sh '''
        set +e
        docker compose -f docker-compose.yml -f docker-compose.ci.yml down -v || true
        rm -f docker-compose.ci.yml .env || true
        docker image rm -f "${APP_IMAGE}" >/dev/null 2>&1 || true
      '''
    }
  }
}
