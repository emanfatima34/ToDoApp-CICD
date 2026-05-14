pipeline {
    agent any

    environment {
        SELENIUM_IMAGE = "taskmaster-selenium-tests"
        // Plain docker (no Compose required on Jenkins)
        WEB_IMAGE = "taskmaster-web"
        DOCKER_NETWORK = "taskmaster_jenkins_net"
        DB_CONTAINER = "taskmaster_mysql"
        WEB_CONTAINER = "taskmaster_web"
    }

    stages {

        stage('Checkout Code') {
            steps {
                git branch: 'main', url: 'https://github.com/emanfatima34/ToDoApp-CICD.git'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m pip install --upgrade pip --break-system-packages
                    python3 -m pip install -r requirements.txt --break-system-packages
                '''
            }
        }

        stage('Unit Testing') {
            steps {
                sh 'export SKIP_DB_AT_IMPORT=1 && python3 -m unittest test_app.py'
            }
        }

        // Build app image (same Dockerfile as docker-compose "web" service)
        stage('Docker Build') {
            steps {
                sh 'docker build -t $WEB_IMAGE .'
            }
        }

        // Run MySQL + Flask on a user-defined network (DB hostname = container name)
        stage('Run Docker Container') {
            steps {
                sh '''
                    set -e
                    if [ -f secrets/db_password.txt ]; then
                      DBPASS=$(tr -d '\n\r' < secrets/db_password.txt)
                    else
                      echo "WARNING: secrets/db_password.txt not found; using default password"
                      DBPASS=mypassword123
                    fi

                    docker rm -f "$WEB_CONTAINER" "$DB_CONTAINER" 2>/dev/null || true
                    docker network rm "$DOCKER_NETWORK" 2>/dev/null || true
                    docker network create "$DOCKER_NETWORK"

                    docker run -d --name "$DB_CONTAINER" --network "$DOCKER_NETWORK" \
                      -e MYSQL_ROOT_PASSWORD="$DBPASS" \
                      -e MYSQL_DATABASE=todoapp \
                      mysql:5.7

                    echo "Waiting for MySQL..."
                    MYSQL_OK=0
                    for i in $(seq 1 60); do
                      if docker exec "$DB_CONTAINER" mysqladmin ping -h localhost -uroot -p"$DBPASS" --silent 2>/dev/null; then
                        echo "MySQL is ready."
                        MYSQL_OK=1
                        break
                      fi
                      sleep 2
                    done
                    if [ "$MYSQL_OK" != "1" ]; then
                      echo "MySQL did not become ready in time"
                      docker logs "$DB_CONTAINER" 2>&1 || true
                      exit 1
                    fi

                    docker run -d --name "$WEB_CONTAINER" --network "$DOCKER_NETWORK" -p 5000:5000 \
                      -e DB_HOST="$DB_CONTAINER" \
                      -e DB_USER=root \
                      -e DB_PASSWORD="$DBPASS" \
                      -e DB_NAME=todoapp \
                      "$WEB_IMAGE"

                    READY=0
                    for i in $(seq 1 30); do
                      if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/', timeout=5)" 2>/dev/null; then
                        READY=1
                        break
                      fi
                      echo "Waiting for TaskMaster on :5000 ($i/30)..."
                      sleep 2
                    done
                    if [ "$READY" != "1" ]; then
                      echo "App did not become ready on port 5000"
                      docker logs "$WEB_CONTAINER" 2>&1 || true
                      docker logs "$DB_CONTAINER" 2>&1 || true
                      exit 1
                    fi
                    echo "TaskMaster is responding."
                '''
            }
        }

        stage('Selenium Testing') {
            steps {
                sh '''
                    docker build -f selenium_tests/Dockerfile -t $SELENIUM_IMAGE .
                    docker run --rm --network host -e APP_BASE_URL=http://127.0.0.1:5000 $SELENIUM_IMAGE
                '''
            }
        }
    }

    post {
        always {
            echo "Pipeline finished"
            sh '''
                docker rm -f "$WEB_CONTAINER" "$DB_CONTAINER" 2>/dev/null || true
                docker network rm "$DOCKER_NETWORK" 2>/dev/null || true
            '''
        }

        success {
            echo "CI/CD Pipeline SUCCESS"
        }

        failure {
            echo "Pipeline FAILED"
        }
    }
}
