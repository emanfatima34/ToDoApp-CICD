pipeline {
    agent any

    environment {
        IMAGE_NAME = "mytodoapp"
        CONTAINER_NAME = "mytodoapp_container"
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
                sh 'python3 -m unittest test_app.py'
            }
        }

        stage('Docker Build') {
            steps {
                sh 'docker build -t $IMAGE_NAME .'
            }
        }

        stage('Run Docker Container') {
            steps {
                sh '''
                docker stop $CONTAINER_NAME || true
                docker rm $CONTAINER_NAME || true
                docker run -d --name $CONTAINER_NAME -p 5000:5000 $IMAGE_NAME
                sleep 5
                '''
            }
        }

        stage('Selenium Testing') {
            steps {
                sh 'python3 selenium_tests/test_ui.py'
            }
        }
    }

    post {
        always {
            echo "Pipeline finished"
        }

        success {
            echo "CI/CD Pipeline SUCCESS"
        }

        failure {
            echo "Pipeline FAILED"
        }
    }
}