pipeline {
    agent any

    environment {
        SONAR_TOKEN = credentials('sonarqube')
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
                withSonarQubeEnv('sonarqube') {
                    sh '''
                        sonar-scanner \
                          -Dsonar.projectKey=car_rental \
                          -Dsonar.sources=. \
                          -Dsonar.host.url=$SONAR_HOST_URL \
                          -Dsonar.login=$SONAR_TOKEN \
                          -Dsonar.language=py \
                          -Dsonar.python.version=3.10
                    '''
                }
            }
        }
    }
}
