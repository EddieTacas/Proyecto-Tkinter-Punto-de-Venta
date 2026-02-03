import qrcode

# Datos que quieres codificar
data = "https://www.ejemplo.com"

# Generar QR
qr = qrcode.make(data)

# Guardar como imagen
qr.save("codigo_qr.png")