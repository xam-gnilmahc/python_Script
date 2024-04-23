<?php

namespace App\Http\Controllers;

use App\Http\Requests\DeployRequest;
use App\Models\CodePipeLineLog;
use Aws\CodePipeline\CodePipelineClient;
use  Aws\CodePipeline\Exception\CodePipelineException;
use Illuminate\Contracts\Session\Session;
use Illuminate\Contracts\View\View;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Config;
use App\Models\Task;
class DeployController extends Controller
{

    //Initializing CodePipeline
    public function initializaeCodePipelineClient() {
        return  new CodePipelineClient([
            'version' => 'latest',
            'region' => 'us-west-1',
            'credentials' => [
                'key' => env('AWS_ACCESS_KEY_ID'),
                'secret' => env('AWS_SECRET_ACCESS_KEY'),
            ],
        ]);
    }

    public function deploy(Request $request) {

        $stage_name = $request['stagging'];
        $project_name = $request['taskInfo']['project_name'];

        if($stage_name) {

                $this->initializaeCodePipelineClient();

                if($stage_name === "development") {

                    $pipelineId = $request['taskInfo']['development_pipeline'];
                    if (empty($pipelineId)) {
                        // Return an error response
                        return response()->json(['pipeline_error' => 'Development pipeline is not set for this project.']);
                    }

                } elseif($stage_name === "production") {

                    $pipelineId = $request['taskInfo']['production_Pipeline'];
                    if (empty($pipelineId)) {

                        return response()->json(['pipeline_error' => 'Production pipeline is not set for this project.']);
                    }
                    else{
                        $response = $this->taskStatus($request,$status='11');
                        return $response;
                    }


                } else {

                    $pipelineId = $request['taskInfo']['staging_pipeline'];
                    if (empty($pipelineId)) {
                        // Return an error response
                        return response()->json(['pipeline_error' => 'Staging pipeline is not set for this project.']);
                    }
                    else{
                        $response =  $this->taskStatus($request,$status='9');
                        return $response;
                    }

                }

                if ($pipelineId) {
                    $pipelineDetails = $this->getPipeLineDetails($pipelineId);
                    return ['pipeline_name' => $pipelineDetails->get('pipelineName'), 'stageStates' => $pipelineDetails->get('stageStates'),'task_details' => $project_name];
                }
            }
        }


    public function getPipeLineDetails($pipelineName) {
        //Listing the details of specific pipeline
         $codePipeline =   $this->initializaeCodePipelineClient();

            $getPipelineDetails = $codePipeline->getPipelineState([
                'name' => $pipelineName,
            ]);
            return $getPipelineDetails;
    }

    public function taskStatus($request,$status){
        $task_id = $request['taskInfo']['taskId'];
        $task = Task::find($task_id);
        if ($task) {
            $task->status = $status;
            $task->save();
            // Return a JSON response indicating success and page refresh is required
            return response()->json(['success' => 'Task status updated successfully.']);
        } else {
             // If task is not found, return a JSON response indicating failure
             return response()->json(['error' => 'Task not found.']);
        }
    }

    public function deployResult(DeployRequest $request)
    {
        $deploy = $request->deploy;

        $deploy_token = $request->deploy_token;

        $manualApproval = $deploy === "Approved" ? "Approved" : "Rejected";

       $codePipeLine =  $this->initializaeCodePipelineClient();

        if ($deploy_token != null) {
            $codePipelineResponse = $codePipeLine->putApprovalResult([
                'actionName' => $request['deploy_action_name'],
                'pipelineName' => $request['deploy_pipeline_name'],
                'result' => [
                    'status' => $deploy,
                    'summary' => "Manual approval ".$manualApproval,
                ],
                'stageName' => $request['deploy_stage_name'],
                'token' => $deploy_token,
            ]);

            if ($codePipelineResponse) {
                 CodePipeLineLog::create([
                    'created_by' => auth()->user()->name,
                    'task_id'     => $request['deploy_taskId'],
                    'project_name' => $request['deploy_projectName'],
                    'deploy' => $request['deploy'],
                    'pull_request' => $request->pull_request ?? null,
                    'commit' => $request->commit ?? null,
                    'summary' => $request->summary ?? null,
                ]);

                return redirect()->back()->with('success', 'Deployed '.$deploy.' Successfully');
            }
        } else {
            return redirect()->back()->with('error', 'Token Missing');
        }
    }


    public function deployLogList(Request $request) {
        $request = $request['project_name'];

        $codePipeLineLogs = CodePipeLineLog::where('project_name',$request)->get();
        return $codePipeLineLogs;
    }
}