//*** Para saber el ID de los grupos de whatsapp y al ejecutarse dara un txt con nombre mis_grupos_whatsapp.txt***//
const { default: makeWASocket, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const pino = require('pino');

async function listGroups() {
    console.log("Loading session...");
    const { state, saveCreds } = await useMultiFileAuthState('auth_baileys');

    const sock = makeWASocket({
        logger: pino({ level: "silent" }),
        printQRInTerminal: true, // Should not happen if session exists
        auth: state,
        connectTimeoutMs: 60000,
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect } = update;

        if (connection === 'open') {
            console.log('Connected! Fetching groups...');

            try {
                // Fetch participating groups
                const groups = await sock.groupFetchAllParticipating();

                const fs = require('fs');
                let output = "--- LISTA DE GRUPOS ---\n";
                const groupIds = Object.keys(groups);

                if (groupIds.length === 0) {
                    output += "No se encontraron grupos.\n";
                } else {
                    groupIds.forEach(id => {
                        const g = groups[id];
                        output += `Nombre: ${g.subject}\n`;
                        output += `ID: ${g.id}\n`;
                        output += "-----------------------\n";
                    });
                }
                output += `\nTotal Grupos: ${groupIds.length}\n`;

                console.log(output);
                fs.writeFileSync('mis_grupos_whatsapp.txt', output, 'utf8');
                console.log("\n✅ Lista guardada en 'mis_grupos_whatsapp.txt'");

                // Close and exit
                process.exit(0);

            } catch (err) {
                console.error("Error fetching groups:", err);
                process.exit(1);
            }
        } else if (connection === 'close') {
            console.log('Connection closed.', lastDisconnect?.error);
            const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== 401;
            if (!shouldReconnect) {
                console.log("Session invalid. Please relink WhatsApp first.");
                process.exit(1);
            }
        }
    });
}

listGroups();
