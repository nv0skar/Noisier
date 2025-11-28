from silence.__main__ import CONFIG


def handle(_):
    from silence.server.endpoint_parser import load_routes

    if CONFIG.get().general.auto_endpoints:
        print("Dumping generated endpoints to the /endpoints/_auto folder...")
        load_routes()
        print("Done!")
    else:
        raise Exception(
            "Endpoint auto generation is disabled in the settings, you need to enable it before you can use this command."
        )
