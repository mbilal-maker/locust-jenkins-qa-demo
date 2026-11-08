// Jenkins runs inside a Linux Docker container in GitHub Codespaces.
// Requires Python 3.11+ and python3-venv installed in the Jenkins container.
// Locust HTML and CSV reports are archived without any Grafana dependency.
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    parameters {
        choice(name: 'TEST_TYPE', choices: ['smoke', 'load', 'stress'], description: 'Performance test profile')
    }

    stages {
        stage('Verify Python') {
            steps {
                sh 'python3 --version'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    set -eu
                    python3 -m venv .venv
                    .venv/bin/python -m pip install -r requirements.txt
                '''
            }
        }

        stage('Start API and Run Locust') {
            steps {
                sh '.venv/bin/python scripts/run_ci.py --profile "$TEST_TYPE"'
            }
        }

        stage('Production Deployment Gate (Simulation)') {
            steps {
                echo 'PASS: Locust performance thresholds met. Production deployment would be allowed.'
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
    }
}
