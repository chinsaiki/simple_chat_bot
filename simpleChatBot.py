import os
import sys
import streamlit.web.bootstrap

# sys.path.append('./')

if __name__ == "__main__":
    # os.chdir(os.path.dirname(__file__))

    flag_options = {
    }

    streamlit.web.bootstrap.load_config_options(flag_options=flag_options)
    flag_options["_is_running_with_streamlit"] = True
    streamlit.web.bootstrap.run(
        "./main.py",
        False,
        "streamlit run",
        flag_options,
    )