#import <Foundation/Foundation.h>
#import <PDFKit/PDFKit.h>

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 2) {
            fprintf(stderr, "Usage: extract_pdf <file.pdf>\n");
            return 2;
        }
        NSString *path = [NSString stringWithUTF8String:argv[1]];
        PDFDocument *document = [[PDFDocument alloc] initWithURL:[NSURL fileURLWithPath:path]];
        if (document == nil) {
            fprintf(stderr, "Cannot open PDF: %s\n", argv[1]);
            return 1;
        }
        for (NSInteger index = 0; index < document.pageCount; index++) {
            NSString *text = [[document pageAtIndex:index] string] ?: @"";
            NSString *encoded = [[text dataUsingEncoding:NSUTF8StringEncoding]
                base64EncodedStringWithOptions:0];
            printf("%ld\t%s\n", (long)index + 1, encoded.UTF8String);
        }
    }
    return 0;
}
