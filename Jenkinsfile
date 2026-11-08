// Windows laptop / Windows Jenkins agent.
// Jenkins plugins: Pipeline, Git, HTML Publisher.
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    parameters {
        choice(name: 'TEST_TYPE', choices: ['smoke', 'load', 'stress'], description: 'Locust load profile')
    }

    triggers {
        // Localhost Jenkins cannot receive GitHub webhooks directly.
        // Check GitHub for new commits every ~2 minutes (Jenkins H may offset the minute).
        pollSCM('H/2 * * * *')
        // Scheduled weekday run; omit this line if you only want push/manual runs.
        cron('H 2 * * 1-5')
    }

    stages {
        stage('Install Python dependencies') {
            steps {
                bat 'python --version'
                bat 'python -m pip install -r requirements.txt'
            }
        }

        stage('Start staging and run Locust') {
            steps {
                // Script starts a temporary API, health-checks, runs Locust,
                // and always shuts down the API. Locust exit code sets build status.
                bat 'python scripts\\run_ci.py --profile %TEST_TYPE%'
            }
        }

        stage('Production deployment (SIMULATION ONLY)') {
            steps {
                echo 'PASS: Performance gate met. Real production deployment would go here.'
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
            publishHTML(target: [
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'reports',
                reportFiles: 'locust-report.html',
                reportName: 'Locust HTML Report'
            ])
        }
    }
}
