pipeline {
    agent any

    environment {
        VENV_DIR = 'env'
    }

    stages {

        stage('Set up Python') {
            steps {
                sh '''
                    python3.11 -m venv $VENV_DIR
                    $VENV_DIR/bin/pip install --upgrade pip
                    $VENV_DIR/bin/pip install -r requirements.txt --no-cache-dir --no-deps
                '''
            }
        }
/*
        stage('Deploy Environment File') {
            steps {
                withCredentials([file(credentialsId: 'my-env-file', variable: 'ENV_FILE')]) {
                    sh '''
                        cp "$ENV_FILE" "$WORKSPACE/.env"
                        sudo cp "$ENV_FILE" /var/lib/jenkins/workspace/Meal-Planner-Backend/.env
                    '''
                }
            }
        }

*/
        stage('Restart FastAPI Service') {
            steps {
                sh '''
                    echo "Reloading systemd and restarting MealPlanner service..."
                    sudo systemctl daemon-reload
                    sudo systemctl restart mealplanner.service
                    sudo systemctl status mealplanner.service --no-pager
                '''
            }
        }
    
/*
        stage('Load Environment') {
            steps {
                withCredentials([file(credentialsId: 'my-env-file', variable: 'ENV_FILE')]) {
                    sh '''
                        echo "Loading environment variables from secure .env file"
                        set -a
                        source "$ENV_FILE"
                        set +a
                        cp "$ENV_FILE" "$WORKSPACE/.env.loaded"
                    '''
                }
            }
        }

        stage('Run Test') {
            steps {
             sh '''
                 echo "Running Unit Tests with pytest..."
                 $VENV_DIR/bin/pytest --maxfail=1 --disable-warnings
             '''
            }
        }
      
        stage('Run App') {
            steps {
                sh '''
                    if [ ! -f "$WORKSPACE/.env.loaded" ]; then
                      echo ".env.loaded file missing"
                      exit 1
                    fi

                    echo "Sourcing .env.loaded..."
                    set -a
                    source "$WORKSPACE/.env.loaded"
                    set +a

                    $VENV_DIR/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
                '''
            }
        }
        */
    }
 

    post {
        failure {
            echo 'Build failed!'
        }
        success {
            echo 'Build succeeded!'
        }
    }
}