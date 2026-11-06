plugins { id("com.android.application") }
android {
    namespace = "net.brozkeff.kitvisionrushtools"
    compileSdk = 37
    defaultConfig { applicationId = "net.brozkeff.kitvisionrushtools"; minSdk = 31; targetSdk = 37; versionCode = 3; versionName = "0.1.2" }
}

tasks.register<Copy>("exportDebugApk") {
    dependsOn("assembleDebug")
    from(layout.buildDirectory.file("outputs/apk/debug/app-debug.apk"))
    into(layout.buildDirectory.dir("outputs/distributions"))
    rename { "net.brozkeff.kitvisionrushtools-${android.defaultConfig.versionName}-debug.apk" }
}
