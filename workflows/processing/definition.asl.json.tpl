{
  "Comment": "FrameOps processing \u2014 asset-type branching, parallel jobs, ECS Fargate sync, retries/timeouts, finalize gate",
  "StartAt": "ChoosePlan",
  "States": {
    "ChoosePlan": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.asset_type",
          "StringEquals": "video",
          "Next": "ParallelVideo"
        },
        {
          "Variable": "$.asset_type",
          "StringEquals": "image",
          "Next": "ParallelImage"
        },
        {
          "Variable": "$.asset_type",
          "StringEquals": "audio",
          "Next": "ParallelAudio"
        },
        {
          "Variable": "$.asset_type",
          "StringEquals": "document",
          "Next": "ParallelDocument"
        }
      ],
      "Default": "ParallelOther"
    },
    "ParallelImage": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "ImageMetadata",
          "States": {
            "ImageMetadata": {
              "Type": "Task",
              "Resource": "arn:aws:states:::ecs:runTask.sync",
              "Parameters": {
                "TaskDefinition": "frameops-${env}-metadata",
                "LaunchType": "FARGATE",
                "Cluster": "${cluster_arn}",
                "NetworkConfiguration": {
                  "AwsvpcConfiguration": {
                    "Subnets": ${private_subnets_json},
                    "SecurityGroups": [
                      "${ecs_security_group}"
                    ],
                    "AssignPublicIp": "DISABLED"
                  }
                }
              },
              "Retry": [
                {
                  "ErrorEquals": [
                    "States.ALL"
                  ],
                  "MaxAttempts": 3,
                  "IntervalSeconds": 2,
                  "BackoffRate": 2.0
                }
              ],
              "Catch": [
                {
                  "ErrorEquals": [
                    "States.ALL"
                  ],
                  "ResultPath": "$.error",
                  "Next": "ImageBranchFailed"
                }
              ],
              "TimeoutSeconds": 300,
              "End": true
            },
            "ImageBranchFailed": {
              "Type": "Fail",
              "Cause": "Image metadata failed"
            }
          }
        },
        {
          "StartAt": "ImageThumbnail",
          "States": {
            "ImageThumbnail": {
              "Type": "Task",
              "Resource": "arn:aws:states:::ecs:runTask.sync",
              "Parameters": {
                "TaskDefinition": "frameops-${env}-thumbnail",
                "LaunchType": "FARGATE",
                "Cluster": "${cluster_arn}",
                "NetworkConfiguration": {
                  "AwsvpcConfiguration": {
                    "Subnets": ${private_subnets_json},
                    "SecurityGroups": [
                      "${ecs_security_group}"
                    ],
                    "AssignPublicIp": "DISABLED"
                  }
                }
              },
              "Retry": [
                {
                  "ErrorEquals": [
                    "States.ALL"
                  ],
                  "MaxAttempts": 3,
                  "IntervalSeconds": 2,
                  "BackoffRate": 2.0
                }
              ],
              "Catch": [
                {
                  "ErrorEquals": [
                    "States.ALL"
                  ],
                  "ResultPath": "$.error",
                  "Next": "ImageThumbFailed"
                }
              ],
              "TimeoutSeconds": 300,
              "End": true
            },
            "ImageThumbFailed": {
              "Type": "Fail",
              "Cause": "Thumbnail failed"
            }
          }
        }
      ],
      "Next": "Finalize",
      "Retry": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "MaxAttempts": 3,
          "IntervalSeconds": 2,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "Next": "TerminalFailure"
        }
      ]
    },
    "ParallelVideo": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "VideoMetadata",
          "States": {
            "VideoMetadata": {
              "Type": "Task",
              "Resource": "arn:aws:states:::ecs:runTask.sync",
              "Parameters": {
                "TaskDefinition": "frameops-${env}-metadata",
                "LaunchType": "FARGATE",
                "Cluster": "${cluster_arn}",
                "NetworkConfiguration": {
                  "AwsvpcConfiguration": {
                    "Subnets": ${private_subnets_json},
                    "SecurityGroups": [
                      "${ecs_security_group}"
                    ],
                    "AssignPublicIp": "DISABLED"
                  }
                }
              },
              "TimeoutSeconds": 300,
              "End": true
            }
          }
        },
        {
          "StartAt": "Transcode1080p",
          "States": {
            "Transcode1080p": {
              "Type": "Task",
              "Resource": "arn:aws:states:::ecs:runTask.sync",
              "Parameters": {
                "TaskDefinition": "frameops-${env}-transcode",
                "LaunchType": "FARGATE",
                "Cluster": "${cluster_arn}",
                "NetworkConfiguration": {
                  "AwsvpcConfiguration": {
                    "Subnets": ${private_subnets_json},
                    "SecurityGroups": [
                      "${ecs_security_group}"
                    ],
                    "AssignPublicIp": "DISABLED"
                  }
                }
              },
              "TimeoutSeconds": 1800,
              "End": true
            }
          }
        },
        {
          "StartAt": "VideoThumbnail",
          "States": {
            "VideoThumbnail": {
              "Type": "Task",
              "Resource": "arn:aws:states:::ecs:runTask.sync",
              "Parameters": {
                "TaskDefinition": "frameops-${env}-thumbnail",
                "LaunchType": "FARGATE",
                "Cluster": "${cluster_arn}",
                "NetworkConfiguration": {
                  "AwsvpcConfiguration": {
                    "Subnets": ${private_subnets_json},
                    "SecurityGroups": [
                      "${ecs_security_group}"
                    ],
                    "AssignPublicIp": "DISABLED"
                  }
                }
              },
              "TimeoutSeconds": 300,
              "End": true
            }
          }
        }
      ],
      "Next": "Finalize"
    },
    "ParallelAudio": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "AudioMetadata",
          "States": {
            "AudioMetadata": {
              "Type": "Task",
              "Resource": "arn:aws:states:::ecs:runTask.sync",
              "Parameters": {
                "TaskDefinition": "frameops-${env}-metadata",
                "LaunchType": "FARGATE",
                "Cluster": "${cluster_arn}",
                "NetworkConfiguration": {
                  "AwsvpcConfiguration": {
                    "Subnets": ${private_subnets_json},
                    "SecurityGroups": [
                      "${ecs_security_group}"
                    ],
                    "AssignPublicIp": "DISABLED"
                  }
                }
              },
              "TimeoutSeconds": 300,
              "End": true
            }
          }
        },
        {
          "StartAt": "AudioNormalize",
          "States": {
            "AudioNormalize": {
              "Type": "Task",
              "Resource": "arn:aws:states:::ecs:runTask.sync",
              "Parameters": {
                "TaskDefinition": "frameops-${env}-audio",
                "LaunchType": "FARGATE",
                "Cluster": "${cluster_arn}",
                "NetworkConfiguration": {
                  "AwsvpcConfiguration": {
                    "Subnets": ${private_subnets_json},
                    "SecurityGroups": [
                      "${ecs_security_group}"
                    ],
                    "AssignPublicIp": "DISABLED"
                  }
                }
              },
              "TimeoutSeconds": 600,
              "End": true
            }
          }
        }
      ],
      "Next": "Finalize"
    },
    "ParallelDocument": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "DocIntegrity",
          "States": {
            "DocIntegrity": {
              "Type": "Task",
              "Resource": "arn:aws:states:::ecs:runTask.sync",
              "Parameters": {
                "TaskDefinition": "frameops-${env}-document",
                "LaunchType": "FARGATE",
                "Cluster": "${cluster_arn}",
                "NetworkConfiguration": {
                  "AwsvpcConfiguration": {
                    "Subnets": ${private_subnets_json},
                    "SecurityGroups": [
                      "${ecs_security_group}"
                    ],
                    "AssignPublicIp": "DISABLED"
                  }
                }
              },
              "TimeoutSeconds": 300,
              "End": true
            }
          }
        },
        {
          "StartAt": "DocMetadata",
          "States": {
            "DocMetadata": {
              "Type": "Task",
              "Resource": "arn:aws:states:::ecs:runTask.sync",
              "Parameters": {
                "TaskDefinition": "frameops-${env}-metadata",
                "LaunchType": "FARGATE",
                "Cluster": "${cluster_arn}",
                "NetworkConfiguration": {
                  "AwsvpcConfiguration": {
                    "Subnets": ${private_subnets_json},
                    "SecurityGroups": [
                      "${ecs_security_group}"
                    ],
                    "AssignPublicIp": "DISABLED"
                  }
                }
              },
              "TimeoutSeconds": 300,
              "End": true
            }
          }
        }
      ],
      "Next": "Finalize"
    },
    "ParallelOther": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "OtherMetadata",
          "States": {
            "OtherMetadata": {
              "Type": "Task",
              "Resource": "arn:aws:states:::ecs:runTask.sync",
              "Parameters": {
                "TaskDefinition": "frameops-${env}-metadata",
                "LaunchType": "FARGATE",
                "Cluster": "${cluster_arn}",
                "NetworkConfiguration": {
                  "AwsvpcConfiguration": {
                    "Subnets": ${private_subnets_json},
                    "SecurityGroups": [
                      "${ecs_security_group}"
                    ],
                    "AssignPublicIp": "DISABLED"
                  }
                }
              },
              "TimeoutSeconds": 300,
              "End": true
            }
          }
        }
      ],
      "Next": "Finalize"
    },
    "Finalize": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${region}:YOUR_AWS_ACCOUNT_ID:function:frameops-${env}-finalizer",
      "Retry": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "MaxAttempts": 2,
          "IntervalSeconds": 2,
          "BackoffRate": 2.0
        }
      ],
      "Next": "CheckResult"
    },
    "CheckResult": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.status",
          "StringEquals": "PUBLISHED",
          "Next": "Succeed"
        }
      ],
      "Default": "TerminalFailure"
    },
    "TerminalFailure": {
      "Type": "Fail",
      "Cause": "Processing failed or incomplete \u2014 quarantine/DLQ",
      "Error": "FrameOpsTerminalFailure"
    },
    "Succeed": {
      "Type": "Succeed"
    }
  }
}