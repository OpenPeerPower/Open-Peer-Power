print ("******before*************")
    try:
        token = smappy.Smappee(client_id, client_secret)
    except:
        print("####### exception caught ##########")
        sys.exit(1)
    print ("******after*************")
    username = client_id
    password = 'Boswald0'
    token.authenticate(username, password)
    service_locations_dict = token.get_service_locations()
    service_locations = service_locations_dict['serviceLocations']
    #info=token.get_service_location_info(service_locations[0]['serviceLocationId'])
    #smappee_list = info["appliances"]
    #print(smappee_list)
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days = 365)
    smappee_list = token.get_costanalysis(service_locations[0]['serviceLocationId'], yesterday, today, 3)
    appliance_list = {}
    for i, v in enumerate(smappee_list):
        appliance_list[v['appliance']['id']] = v
    #print(appliance_list)
    #exit_code = setup_and_run_opp()
    #pid = subprocess.Popen(["python", "scriptname.py"], creationflags=subprocess.DETACHED_PROCESS).pid
    #pid = subprocess.Popen(["c:/temp/OPP-ui/npm", "start"], cwd='c:/temp/OPP-ui').pid
    # latest pid = subprocess.Popen(["npm", "start"], cwd='C:/Users/Paul/Documents/github/OpenPeerPower/OPP-ui').pid
    #asyncio.get_event_loop().run_until_complete(
    #    websockets.serve(counter, 'localhost', 6789))
