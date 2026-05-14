pipeline {
    agent any

    environment {
        // Docker Compose project prefix (containers: taskmaster_web, taskmaster_db)
        COMPOSE_PROJECT_NAME = "taskmaster"
        SELENIUM_IMAGE = "taskmaster-selenium-tests"
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
                // Hostname "db" only exists on the Compose network, not on the Jenkins VM.
                sh 'export SKIP_DB_AT_IMPORT=1 && python3 -m unittest test_app.py'
            }
        }

        stage('Docker Build') {
            steps {
                sh 'docker compose build'
            }
        }

        stage('Run Docker Container') {
            steps {
                sh '''
                    docker compose down || true
                    docker compose up -d
                    READY=0
                    for i in $(seq 1 30); do
                      if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/', timeout=5)" 2>/dev/null; then
                        READY=1
                        break
                      fi
                      echo "Waiting for TaskMaster web on :5000 ($i/30)..."
                      sleep 2
                    done
                    if [ "$READY" != "1" ]; then
                      echo "App did not become ready on port 5000"
                      docker compose logs --no-color || true
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
            sh 'docker compose down || true'
        }

        success {
            echo "CI/CD Pipeline SUCCESS"
        }

        failure {
            echo "Pipeline FAILED"
        }
    }
}
