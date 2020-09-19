def format_code(data:list) -> any:
    # sublime completion result [(label,value)]
    if not data:
        return None
    
    parse = [("{}\t{}".format(cmpl["label"],cmpl["kind"]),cmpl["label"]) for cmpl in data]
    return parse