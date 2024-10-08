
 public function index()
    {
        ini_set('memory_limit',-1);
        ini_set('max_execution_time', 0);

        WorkOS::setApiKey(self::WORKOS_API_KEY);

        $userCollection = collect();
        $mangerIds = [];

        try {
            $pageAfter = null;
            do {

                list($before, $after, $usersLists) = (new DirectorySync())
                    ->listUsers(self::WORKOS_DIRECTORY, null, 100, null, $pageAfter, 'asc');

                foreach($usersLists as $users)
                {
                    $userss = (array) $users;
                    $user = $userss['raw'];

                    if($user['state'] == 'active')
                    {
                        $employeeNumber = $user['raw_attributes']['urn:ietf:params:scim:schemas:extension:enterprise:2.0:User']['employeeNumber'];
                        $managerId = NULL;
                        $manager = $user['raw_attributes']['urn:ietf:params:scim:schemas:extension:enterprise:2.0:User'];

                        if(array_key_exists('manager', $manager)){

                              $managerId =  $manager['manager']['value'];
                              if (!in_array($managerId, $mangerIds)) {
                                  array_push($mangerIds, $managerId);
                              }
                        }else {
                            if (!in_array($employeeNumber, $mangerIds)) {
                                array_push($mangerIds, $employeeNumber);
                            }
                        }

                        $userFullName = $user['first_name'] . ' '. $user['last_name'];
                        $userCollection->push(
                            [
                                'name' => $userFullName,
                                'managerId' => $managerId,
                                "employNumber" => $employeeNumber,
                            ]);
                    }
                }

                $pageAfter = $after;
            } while ($pageAfter);

            $filenameManager = 'csvManager.csv';
            $filename = 'csvManagerClients.csv';

            $pathManger = storage_path('csv/'. $filenameManager);
            $path = storage_path('csv/'. $filename);

            $fileHandleManger = fopen($pathManger, 'w');
            $fileHandle = fopen($path, 'w');

            foreach($mangerIds as $mangerId)
            {
                $manager = collect($userCollection->filter(function ($item) use ($mangerId) {
                    return $item['employNumber'] == $mangerId;
                })->all())->pluck('name');


                if($manager->isNotEmpty())
                {
                    fputcsv($fileHandleManger, $manager->toArray());

                    $names =  collect($userCollection->filter(function ($item) use ($mangerId) {
                        return $item['managerId'] == $mangerId;
                    })->all())->pluck('name')->prepend($manager[0]);

                    fputcsv($fileHandle, $names->toArray());
                }
            }

            fclose($fileHandle);
            fclose($fileHandleManger);

        }catch (\Exception $exception){
            dd($exception);
        }

        return response()->json("Completed");
    }