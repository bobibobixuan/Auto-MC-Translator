from mc_ai_translator.ui import build_app, build_launch_kwargs

app = build_app()


if __name__ == "__main__":
    app.launch(inbrowser=True, **build_launch_kwargs())
