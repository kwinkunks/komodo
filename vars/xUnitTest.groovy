def call(Map args = [:]) {
    def job_name = args.job_name
    def test_script = args.test_script ? args.test_script : "ci/jenkins/testkomodo.sh"
    def time_out = args.time_out ? args.time_out : 60

    pipeline {
        agent { label 'master||orchestrating'}
        options {
            timeout(time: "${time_out}", unit: 'MINUTES')
        }

        parameters {
            string(name: 'RELEASE_BASE', defaultValue: "bleeding", description: 'The release base that is to be tested. I.e. bleeding or 2020.06.05.')
        }

        environment {
            SUB_JOB_NAME = "${job_name}"
            TEST_SCRIPT = "${test_script}"
        }

        stages {
            stage('Test Matrix') {
                matrix {
                    agent { label 'master||orchestrating' }
                    axes {
                        axis {
                            name 'RH_VERSION'
                            values '7'
                        }
                        axis {
                            name 'PY_VERSION'
                            values '3.8'
                        }
                    }
                    stages {
                        stage('Run PR job') {
                            steps {
                                build job: "${env.SUB_JOB_NAME}", parameters: [
                                    string(name: 'KOMODO_RELEASE', value: "${params.RELEASE_BASE}-py${PY_VERSION.replace(".", "")}-rhel${RH_VERSION}"),
                                    string(name: 'ghprbPullId', value: "${params.ghprbPullId}"),
                                    string(name: 'TEST_SCRIPT', value: "${env.TEST_SCRIPT}"),
                                ], wait: true
                            }
                        }
                    }
                }
            }
        }
    }
}
