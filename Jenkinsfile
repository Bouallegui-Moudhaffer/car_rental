pipeline {
    agent any

    environment {
        SONAR_TOKEN = credentials('sonarqube') // Correct use for declarative environment
    }

    stages {
        stage('Checkout GIT') {
            steps {
                git branch: 'wassim',
                    url: 'git@github.com:Bouallegui-Moudhaffer/car_rental.git',
                    credentialsId: 'git'
            }
        }

        stage('Maven Clean') {
            steps {
                sh 'mvn clean install'
            }
        }

        stage('Maven Package') {
            steps {
                sh 'mvn package -DskipTests'
            }
        }

        stage('SonarQube Analysis') {
            steps {
                sh 'mvn sonar:sonar -Dsonar.token=$SONAR_TOKEN'
            }
        }
    }
}
