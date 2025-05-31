# PowerShell script to generate self-signed SSL certificates for development
# Run this script as administrator

# Create directory for SSL certificates if it doesn't exist
$sslDir = ".\nginx\ssl"
if (-not (Test-Path $sslDir)) {
    New-Item -ItemType Directory -Path $sslDir -Force
}

# Generate self-signed certificate
$cert = New-SelfSignedCertificate -DnsName "localhost" -CertStoreLocation "cert:\LocalMachine\My" -NotAfter (Get-Date).AddYears(1)

# Export certificate to PFX format
$certPassword = ConvertTo-SecureString -String "password" -Force -AsPlainText
$pfxPath = Join-Path -Path $sslDir -ChildPath "server.pfx"
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $certPassword

# Export certificate to CRT format
$crtPath = Join-Path -Path $sslDir -ChildPath "server.crt"
Export-Certificate -Cert $cert -FilePath $crtPath -Type CERT

# Export private key to PEM format
$keyPath = Join-Path -Path $sslDir -ChildPath "server.key"
$privateKeyBytes = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($cert).Key.Export([System.Security.Cryptography.CngKeyBlobFormat]::Pkcs8PrivateBlob)
[System.IO.File]::WriteAllBytes($keyPath, $privateKeyBytes)

Write-Host "Self-signed SSL certificates generated successfully:"
Write-Host "Certificate: $crtPath"
Write-Host "Private Key: $keyPath"
Write-Host "PFX File: $pfxPath"
