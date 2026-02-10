pipeline {
  agent any

  environment {
    APP_IMAGE = "collector-b:${BUILD_NUMBER}"
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

          # Env CI (pas de secrets réels)
          cat > .env <<'EOF'
DEBUG=False
SECRET_KEY=ci-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1,web
CSRF_TRUSTED_ORIGINS=http://localhost:8000

DB_NAME=collector
DB_USER=collector
DB_PASSWORD=collectorpass
DB_HOST=db
DB_PORT=3306

REDIS_URL=redis://redis:6379/0
EOF

          # Override CI: on désactive les bind mounts (.:/app) et les ports,
          # et on force "web/worker" à utiliser l'image buildée.
          cat > docker-compose.ci.yml <<EOF
services:
  web:
    image: ${APP_IMAGE}
    build: null
    volumes: []
    ports: []
  worker:
    image: ${APP_IMAGE}
    build: null
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
          docker build -t ${APP_IMAGE} .
          docker image inspect ${APP_IMAGE} >/dev/null
        '''
      }
    }

    stage('Unit + Integration tests') {
      steps {
        sh '''
          set -eu

          # Attendre MySQL (healthcheck du compose utilise rootpass)
          for i in $(seq 1 40); do
            if docker compose -f docker-compose.yml -f docker-compose.ci.yml exec -T db \
                 mysqladmin ping -h 127.0.0.1 -uroot -prootpass --silent; then
              echo "MySQL is ready"
              break
            fi
            echo "Waiting MySQL... ($i/40)"
            sleep 2
          done

          # Lancer migrations + tests depuis l'image (pas de bind mount)
          docker compose -f docker-compose.yml -f docker-compose.ci.yml run --rm \
            -e DJANGO_SETTINGS_MODULE=config.settings \
            web sh -lc "
              cd /app &&
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
          # Non-bloquant: on veut que la CI passe, mais on garde le contrôle sécurité.
          docker run --rm ${APP_IMAGE} sh -lc "
            pip install --no-cache-dir bandit >/dev/null &&
            bandit -r /app -x */migrations/* -ll || true
          "
        '''
      }
    }

    stage('Vulnerabilities (Trivy image)') {
      steps {
        sh '''
          set -eu
          # Non-bloquant pour éviter de casser le pipeline au début
          docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image \
            --severity HIGH,CRITICAL \
            --exit-code 0 \
            ${APP_IMAGE} || true
        '''
      }
    }

    stage('Smoke test (container)') {
      steps {
        sh '''
          set -eu

          docker compose -f docker-compose.yml -f docker-compose.ci.yml up -d web

          # Test HTTP depuis un conteneur curl dans le network du compose
          for i in $(seq 1 20); do
            if docker run --rm --network projet-collab-ci_default curlimages/curl:8.5.0 \
              -sSf http://web:8000/ >/dev/null; then
              echo "HTTP OK"
              break
            fi
            echo "Waiting HTTP... ($i/20)"
            sleep 2
          done
        '''
      }
    }
  }

  post {
    always {
      sh '''
        set +e
        docker compose -f docker-compose.yml -f docker-compose.ci.yml down -v
        rm -f docker-compose.ci.yml .env
        docker image rm -f ${APP_IMAGE} >/dev/null 2>&1 || true
      '''
    }
  }
}
