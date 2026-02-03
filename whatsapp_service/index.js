//*** Para iniciar whatsapp ***//
const { default: makeWASocket, DisconnectReason, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const express = require('express');
const pino = require('pino');
const cors = require('cors');
const fs = require('fs');
const app = express();
const PORT = 3000;

app.use(express.json());
app.use(cors());

let sock;
let qrCode = null;
let status = 'DISCONNECTED'; // CONNECTED, QR_NEEDED, DISCONNECTED, CONNECTING
let connectionRetryCount = 0;

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('auth_baileys');

    status = 'CONNECTING';

    sock = makeWASocket({
        logger: pino({ level: "silent" }),
        printQRInTerminal: false,
        auth: state,
        defaultQueryTimeoutMs: undefined,
        connectTimeoutMs: 60000,
        keepAliveIntervalMs: 10000,
        retryRequestDelayMs: 2000
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            qrCode = qr;
            status = 'QR_NEEDED';
            console.log('QR Loop received');
        }

        if (connection === 'close') {
            const reason = (lastDisconnect?.error)?.output?.statusCode;
            const shouldReconnect = reason !== DisconnectReason.loggedOut;

            // If reconnecting, keep status as CONNECTING so UI knows we are trying
            status = shouldReconnect ? 'CONNECTING' : 'DISCONNECTED';
            qrCode = null;
            console.log('Connection closed. Reason:', reason, 'Error:', lastDisconnect?.error, 'Reconnecting:', shouldReconnect);

            if (shouldReconnect) {
                if (connectionRetryCount < 10) {
                    connectionRetryCount++;
                    const delay = Math.min(connectionRetryCount * 2000, 10000);
                    console.log(`Reconnecting in ${delay}ms... (Attempt ${connectionRetryCount})`);
                    setTimeout(connectToWhatsApp, delay);
                } else {
                    console.log("Max retries reached. Waiting for manual restart.");
                }
            } else {
                console.log('Logged out. Please clear session and scan QR again.');
                try {
                    fs.rmSync('auth_baileys', { recursive: true, force: true });
                    console.log('Session cleared. Restarting to generate new QR...');
                    status = 'DISCONNECTED';
                    // Optional: Auto-restart or let user trigger.
                    // If we auto-restart, we get a QR immediately.
                    connectToWhatsApp();
                } catch (err) {
                    console.error('Failed to clear session:', err);
                }
            }
        } else if (connection === 'open') {
            console.log('opened connection');
            status = 'CONNECTED';
            connectionRetryCount = 0;
            qrCode = null;
        }
    });
}

// Routes
app.get('/status', (req, res) => {
    res.json({ status, qr: qrCode, retryCount: connectionRetryCount });
});

app.get('/qr', (req, res) => {
    if (qrCode) {
        res.json({ success: true, qr: qrCode });
    } else {
        res.json({ success: false, message: "No QR available (maybe connected or connecting)", status: status });
    }
});

app.post('/connect', (req, res) => {
    console.log("Manual connect requested");
    if (status === 'CONNECTED') {
        return res.json({ success: true, message: "Already connected" });
    }
    // Reset retry count to allow new attempts
    connectionRetryCount = 0;

    // If we are already connecting, we might just want to let it run, 
    // OR if it's stuck, we might want to force it?
    // Calling connectToWhatsApp() twice might safely re-init if handled correctly,
    // but Baileys `makeWASocket` creates a NEW socket. Old one might leak if not closed?
    // But `sock` is global.
    // For simplicity, let's only call if not connecting/qr needed, OR if we want to force restart.
    // If status is DISCONNECTED, call it.
    if (status === 'DISCONNECTED') {
        connectToWhatsApp();
        res.json({ success: true, message: "Connection initiated" });
    } else {
        res.json({ success: true, message: "Already connecting or QR pending. Retries reset." });
    }
});

app.post('/send', async (req, res) => {
    const { number, message } = req.body;

    if (status !== 'CONNECTED' || !sock) {
        return res.status(503).json({ success: false, message: "WhatsApp not connected" });
    }

    try {
        // Format number: e.g. "51999999999@s.whatsapp.net"
        // Input might be just "999999999". Add remoteJid logic.
        let jid = number;
        if (jid.includes('@g.us')) {
            jid = jid.trim();
        } else if (!jid.includes('@s.whatsapp.net')) {
            // Remove non-numeric
            jid = jid.replace(/\D/g, '');
            // Append country code if missing? User should probably provide it in config or we append 51 by default?
            // Baileys needs country code. Let's assume input has it or we default to 51 (Peru) if length is 9.
            if (jid.length === 9) {
                jid = "51" + jid;
            }
            jid = jid + "@s.whatsapp.net";
        }

        // Send
        const sentMsg = await sock.sendMessage(jid, { text: message });
        res.json({ success: true, data: sentMsg });
    } catch (error) {
        console.error("Error sending message:", error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Start
app.listen(PORT, () => {
    console.log(`WhatsApp Service listening on port ${PORT}`);
    connectToWhatsApp();
});
