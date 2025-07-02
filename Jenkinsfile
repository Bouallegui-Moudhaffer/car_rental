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


        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv(installationName: 'sql'){
                    sh './mvnw clean org. sonarsource.scanner-maven: sonar-maven-plugin: 3.9.0.2155:sonar'
                }
            }
        }
    }
}
