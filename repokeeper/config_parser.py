import configparser
from typing import List, Tuple

def get_conf_content(conffile: str, reponame: str) -> Tuple[List[str], str, str, str]:
    try:
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(conffile)

        required_sections = ["options", "packages"]
        for sect in required_sections:
            if sect not in config.sections():
                raise ValueError("packages {} is missing in conf file".format(sect))

        packages = [k.split()[0] for k,v in config["packages"].items()]
        repo_dir = str(config["options"]["repodir"])
        build_dir = str(config["options"]["builddir"])
        repo_name = str(config["options"].get("reponame", reponame))

        return packages, repo_dir, build_dir, repo_name
    except KeyError as ke:
        raise ValueError("Config file parsing failed for missing key: {}".format(str(ke)))

