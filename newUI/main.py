from GUIr import App

if __name__ == "__main__":
    app = App()
    try:
        app.run()
    except KeyboardInterrupt:
        app.on_closing()
    finally:
        print("Done.")
