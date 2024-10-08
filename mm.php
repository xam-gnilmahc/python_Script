public function orders(){
        $data = $request->input('detail');

        \Log::info($data);

        $customerId = $data['customerId'];
        $memberId = $data['memberId'];
        $badgeId = $data['badgeId'];
        $saleId = $data['saleId'];

        $order = Sale::with('purchasedItems', 'shippingAddress')
            ->where([['customerId', $customerId], ['memberId', $memberId], ['badgeId', $badgeId]])
            ->find($saleId);
        $isNonVox = $order->nonVoxFulfilled;

        $apiToken = $data['apiToken'] ?: \App\Models\InventoryOwner::find($order->inventoryOwnerId)?->apiToken;

        if (!$order) {
            return $this->failure('Sales Data Not Found.');
        }
        if ($status == 0 && $isNonVox == '0') {

            foreach ($order->purchasedItems as $lineItem) {
                $itemDetails[] = [
                    'itemSkuNumber'     => $lineItem->sku,
                    'itemQty'           => $lineItem->quantity,
                    'itemName'          => $lineItem->name,
                ];
            }

            $orderShippingAddress = [
                'firstName'    => $order->shippingAddress->firstName,
                'lastName'     => $order->shippingAddress->lastName,
                'email'        => $order->email,
                'address1'     => $order->shippingAddress->address1,
                'address2'     => $order->shippingAddress->address2,
                'city'         => $order->shippingAddress->city,
                'state'        => $order->shippingAddress->state,
                'zip'          => $order->shippingAddress->zip,
                'country'      => $order->shippingAddress->country,
                'phone1'       => $order->shippingAddress->phoneNumber,
            ];

            $client = new Client([
                'verify' => false,
            ]);

            $response = $client->request('POST', 'https://api.voxships.com/orders/createOrder', [
                'json' => [
                    'orderNumber'                 => $order->id,
                    'shipMethod'                  => $order->shipMethod,
                    'orderDate'                   => $order->created_at,
                    'productItems'                => $itemDetails,
                    'orderShippingAddress'        => $orderShippingAddress,
                ],
                'headers' => ['apiToken' => $apiToken],
            ]);

            $getContents = $response->getBody()->getContents();
            $responseData = json_decode($getContents, true);

            if (isset($responseData['returnType']) && $responseData['returnType'] == 'success') {
                $order->flag = 1;
                $order->apiComment = $responseData['result']['orderId'];
            } else {
                $order->flag = 2;
                $order->apiComment = $responseData['message'];
            }

            $order->save();
        }
    }