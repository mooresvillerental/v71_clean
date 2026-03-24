from pathlib import Path

file = Path("api_server_stdlib.py")
code = file.read_text()

insert = '''

        if self.path == "/assistant-set-portfolio":
            length = int(self.headers.get("Content-Length",0))
            body = self.rfile.read(length)
            data = json.loads(body.decode())

            save_portfolio(data)

            return self.send_json({
                "status":"portfolio_updated",
                "portfolio":data
            })
'''

if "/assistant-set-portfolio" not in code:
    code = code.replace("if self.path == \"/assistant-confirm\":", insert + "\n        if self.path == \"/assistant-confirm\":")
    file.write_text(code)
    print("Portfolio update endpoint added")
else:
    print("Endpoint already exists")
