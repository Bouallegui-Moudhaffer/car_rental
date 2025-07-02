pipeline {
    agent any

    environment {
        // aa
        // Define your SonarQube token and other environment variables if necessary
        SONAR_TOKEN = credentials('sonarqube')

    }

    stages {
        stage('Checkout GIT') {
            steps {
                git branch: 'Mohamedwassimghamgui-5NIDS1',
                    url: 'git@github.com:bitri12/5NIDS1-TPFOYER.git',
                    credentialsId: 'github'
            }
        }
        stage('Maven Clean') {
            steps{
                sh "mvn clean install"
            }
        }
        stage('Maven Package'){
            steps{
                sh "mvn package -DskipTests"
            }
        }

        stage('SonarQube Analysis') {
            steps {
                // Run SonarQube analysis
                withCredentials([string(credentialsId: 'sonarqube', variable: 'SONAR_TOKEN')]) {
                    sh 'mvn sonar:sonar -Dsonar.token=${SONAR_TOKEN}'
                }
            }
        }







}