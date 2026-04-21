// client/extension.js
const { LanguageClient, TransportKind } = require('vscode-languageclient/node');

let client;

function activate(context) {
    const serverOptions = {
        command: 'python',
        args: ['-m', 'lpp.server'],
        transport: TransportKind.stdio,
    };
    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'lpp' }],
    };
    client = new LanguageClient(
        'lpp',
        'L++ Language Server',
        serverOptions,
        clientOptions,
    );
    client.start();
    context.subscriptions.push(client);
}

function deactivate() {
    if (client) return client.stop();
}

module.exports = { activate, deactivate };
